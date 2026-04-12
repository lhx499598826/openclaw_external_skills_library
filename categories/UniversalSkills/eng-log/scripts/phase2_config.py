#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import re
from common import VAULT, parse_frontmatter, slug, make_index_id, make_candidate_id, now_utc_iso, read_reports_list_yaml

INDEX_DIR = VAULT / 'index'
CONFIGS_DIR = INDEX_DIR / 'configs'
CANDIDATES_DIR = INDEX_DIR / '_candidates' / 'configs'
MERGES_FILE = INDEX_DIR / 'merge-map.json'
REPORTS_DIR = VAULT / 'reports'
CONFIG_PATTERNS = [re.compile(r'`([A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+)`'), re.compile(r'\b([A-Za-z0-9_-]+\.[A-Za-z0-9_.-]+)\b')]


def canonical_config_name(key: str) -> str:
    return f'config-{slug(key)}'


def extract_config_candidates(content: str):
    found = set()
    for pattern in CONFIG_PATTERNS:
        for match in pattern.findall(content):
            key = match.strip('`').strip()
            if '.' not in key or '/' in key or key.lower().endswith(('.md', '.py', '.json', '.service')):
                continue
            found.add(key)
    return sorted(found)


def write_candidate(canonical: str, alias: str, report_id: str, report_rel: str, occurrence_count: int, threshold: int):
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    path = CANDIDATES_DIR / f'{canonical}.yaml'
    content = f"""type: candidate
candidate_id: {make_candidate_id('config', canonical)}
candidate_type: config
canonical_name: {canonical}
observed_aliases:
  - {alias}
source_reports:
  - {report_id}
source_paths:
  - {report_rel}
occurrence_count: {occurrence_count}
status: candidate
promotion_rule: occurrence_count >= {threshold}
last_seen_at: {now_utc_iso()}
expires_at: null
reason: below threshold
"""
    path.write_text(content, encoding='utf-8')
    return path


def load_merge_map():
    if MERGES_FILE.exists():
        return json.loads(MERGES_FILE.read_text(encoding='utf-8'))
    return {'merged': {}}


def save_merge_map(data):
    MERGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    MERGES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def upsert_config_index(canonical: str, alias: str, report_id: str, report_rel: str):
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIGS_DIR / f'{canonical}.md'
    if path.exists():
        content = path.read_text(encoding='utf-8')
        if alias not in content:
            content = content.replace('aliases:\n', f'aliases:\n  - {alias}\n', 1)
        if f'  - {report_id}\n' not in content:
            content = content.replace('source_reports:\n', f'source_reports:\n  - {report_id}\n', 1)
        if f'  - {report_rel}\n' not in content:
            content = content.replace('source_paths:\n', f'source_paths:\n  - {report_rel}\n', 1)
        if f'- [[{report_rel}]]' not in content:
            content = content.replace('## Related Reports\n', f'## Related Reports\n- [[{report_rel}]]\n', 1)
        path.write_text(content, encoding='utf-8')
    else:
        idx = make_index_id('config', canonical)
        content = f"""---
index_id: {idx}
type: index
index_type: config
canonical_name: {canonical}
aliases:
  - {alias}
status: active
source_reports:
  - {report_id}
source_paths:
  - {report_rel}
---

# {canonical}

## Location
Unknown in Phase 2, inspect linked reports for exact config location.

## Function
Derived from reports mentioning this config key.

## Impact
Unknown in Phase 2, inspect linked reports.

## Compatibility / Update Notes
Unknown in Phase 2.

## Related Reports
- [[{report_rel}]]

## Related Components

## Related Features/Workflows

## Notes
Phase 2 auto-generated config index.
"""
        path.write_text(content, encoding='utf-8')
    return path


def collect_configs():
    counts, mapping = {}, {}
    for entry in read_reports_list_yaml().get('reports', []):
        report = VAULT / entry['path']
        content = report.read_text(encoding='utf-8')
        for key in extract_config_candidates(content):
            canon = canonical_config_name(key)
            counts[canon] = counts.get(canon, 0) + 1
            mapping.setdefault(canon, []).append((key, entry['report_id'], entry['path']))
    return counts, mapping


def build(dry_run=False):
    results = {'configs_to_create': [], 'candidate_updates': []}
    counts, mapping = collect_configs()
    for canon, items in mapping.items():
        if counts[canon] >= 2:
            for key, report_id, report_rel in items:
                if dry_run:
                    results['configs_to_create'].append(canon)
                else:
                    upsert_config_index(canon, key, report_id, report_rel)
                    results['configs_to_create'].append(str(CONFIGS_DIR / f'{canon}.md'))
        else:
            for key, report_id, report_rel in items:
                if dry_run:
                    results['candidate_updates'].append(canon)
                else:
                    results['candidate_updates'].append(str(write_candidate(canon, key, report_id, report_rel, counts[canon], 2)))
    return results


def merge(old_name: str, canonical_name: str):
    data = load_merge_map()
    data.setdefault('merged', {})[old_name] = canonical_name
    save_merge_map(data)
    return {'old': old_name, 'canonical': canonical_name}


def check():
    failed = False
    results = {'configs': []}
    for path in sorted(CONFIGS_DIR.glob('*.md')):
        content = path.read_text(encoding='utf-8')
        ok = 'index_id:' in content and 'canonical_name:' in content and '## Related Reports' in content
        results['configs'].append({'path': str(path), 'ok': ok})
        failed = failed or not ok
    print(json.dumps({'ok': not failed, 'results': results}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_build = sub.add_parser('build'); p_build.add_argument('--dry-run', action='store_true')
    p_merge = sub.add_parser('merge'); p_merge.add_argument('old_name'); p_merge.add_argument('canonical_name')
    sub.add_parser('check')
    args = parser.parse_args()
    if args.cmd == 'build':
        print(json.dumps({'ok': True, 'result': build(dry_run=args.dry_run), 'mode': 'dry-run' if args.dry_run else 'apply'}, ensure_ascii=False, indent=2)); return 0
    if args.cmd == 'merge':
        print(json.dumps({'ok': True, 'result': merge(args.old_name, args.canonical_name)}, ensure_ascii=False, indent=2)); return 0
    if args.cmd == 'check':
        return check()
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
