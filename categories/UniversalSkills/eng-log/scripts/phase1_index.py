#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
from common import VAULT, parse_frontmatter, slug, make_index_id, make_candidate_id, now_utc_iso, read_reports_list_yaml

INDEX_DIR = VAULT / 'index'
EVENTS_DIR = INDEX_DIR / 'events'
COMPONENTS_DIR = INDEX_DIR / 'components'
CANDIDATES_BASE = INDEX_DIR / '_candidates'
REPORTS_DIR = VAULT / 'reports'


def canonical_component_name(value: str) -> str:
    base = Path(value).name if '/' in value else value
    base = base.replace('.json', ' json').replace('.service', ' service').replace('.py', ' py').replace('.md', ' md')
    return f'component-{slug(base)}'


def event_canonical(meta: dict) -> str:
    return f"event-{slug(meta.get('title', 'event'))}"


def should_create_event(meta: dict) -> bool:
    status = (meta.get('status') or '').lower()
    title = (meta.get('title') or '').lower()
    archive_level = meta.get('archive_level', 'L1')
    if status in {'incident', 'failed', 'investigation'}:
        return True
    if archive_level == 'L1':
        return True
    if any(k in title for k in ['migration', 'deploy', 'incident', 'failure', 'debug']):
        return True
    return False


def write_candidate(candidate_type: str, canonical: str, alias: str, report_id: str, report_rel: str, occurrence_count: int, threshold: int):
    dir_path = CANDIDATES_BASE / f'{candidate_type}s'
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f'{canonical}.yaml'
    data = {
        'type': 'candidate',
        'candidate_id': make_candidate_id(candidate_type, canonical),
        'candidate_type': candidate_type,
        'canonical_name': canonical,
        'observed_aliases': [alias],
        'source_reports': [report_id],
        'source_paths': [report_rel],
        'occurrence_count': occurrence_count,
        'status': 'candidate',
        'promotion_rule': f'occurrence_count >= {threshold}',
        'last_seen_at': now_utc_iso(),
        'expires_at': None,
        'reason': 'below threshold'
    }
    lines = []
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f'{k}:')
            for item in v:
                lines.append(f'  - {item}')
        else:
            lines.append(f'{k}: {v}')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def write_event_index(meta: dict, report_id: str, report_rel: str):
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    canonical = event_canonical(meta)
    index_id = make_index_id('event', canonical)
    path = EVENTS_DIR / f'{canonical}.md'
    title = meta.get('title', canonical)
    date = meta.get('date', '')
    status = meta.get('status', '')
    content = f"""---
index_id: {index_id}
type: index
index_type: event
canonical_name: {canonical}
aliases:
  - {title}
status: active
source_reports:
  - {report_id}
source_paths:
  - {report_rel}
---

# {canonical}

## Summary
{title}

## Time
{date}

## Trigger
Derived from report `{report_rel}`.

## Related Reports
- [[{report_rel}]]

## Related Components

## Related Configs

## Related Features/Workflows

## Current Status
{status}

## Notes
Phase 1 auto-generated event index.
"""
    path.write_text(content, encoding='utf-8')
    return path


def upsert_component_index(canonical: str, alias: str, report_id: str, report_rel: str, component_value: str):
    COMPONENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = COMPONENTS_DIR / f'{canonical}.md'
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
        index_id = make_index_id('component', canonical)
        content = f"""---
index_id: {index_id}
type: index
index_type: component
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

## Path
{component_value}

## Purpose
Derived from reports mentioning this component.

## Related Reports
- [[{report_rel}]]

## Related Configs

## Related Features/Workflows

## Known Impact
Unknown in Phase 1, inspect linked reports.

## Notes
Phase 1 auto-generated component index.
"""
        path.write_text(content, encoding='utf-8')
    return path


def build_indexes(dry_run=False):
    results = {'events_to_create': [], 'components_to_create': [], 'candidate_updates': []}
    reports_data = read_reports_list_yaml().get('reports', [])
    counts = {}
    mapping = {}
    for entry in reports_data:
        for item in entry.get('files_touched', []):
            canon = canonical_component_name(item)
            counts[canon] = counts.get(canon, 0) + 1
            mapping.setdefault(canon, []).append((item, entry['report_id'], entry['path']))
    for entry in reports_data:
        report_path = VAULT / entry['path']
        meta = parse_frontmatter(report_path.read_text(encoding='utf-8'))
        if should_create_event(meta):
            if dry_run:
                results['events_to_create'].append(event_canonical(meta))
            else:
                results['events_to_create'].append(str(write_event_index(meta, entry['report_id'], entry['path'])))
    for canon, items in mapping.items():
        if counts[canon] >= 2:
            for item, report_id, report_rel in items:
                if dry_run:
                    results['components_to_create'].append(canon)
                else:
                    upsert_component_index(canon, item, report_id, report_rel, item)
                    results['components_to_create'].append(str(COMPONENTS_DIR / f'{canon}.md'))
        else:
            for item, report_id, report_rel in items:
                if dry_run:
                    results['candidate_updates'].append(canon)
                else:
                    results['candidate_updates'].append(str(write_candidate('component', canon, item, report_id, report_rel, counts[canon], 2)))
    return results


def check_indexes():
    results = {'events': [], 'components': []}
    failed = False
    for path in sorted(EVENTS_DIR.glob('*.md')):
        c = path.read_text(encoding='utf-8')
        ok = 'index_id:' in c and 'canonical_name:' in c and '## Related Reports' in c
        results['events'].append({'path': str(path), 'ok': ok})
        failed = failed or not ok
    for path in sorted(COMPONENTS_DIR.glob('*.md')):
        c = path.read_text(encoding='utf-8')
        ok = 'index_id:' in c and 'canonical_name:' in c and '## Path' in c
        results['components'].append({'path': str(path), 'ok': ok})
        failed = failed or not ok
    print(json.dumps({'ok': not failed, 'results': results}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_build = sub.add_parser('build'); p_build.add_argument('--dry-run', action='store_true')
    sub.add_parser('check')
    args = parser.parse_args()
    if args.cmd == 'build':
        print(json.dumps({'ok': True, 'result': build_indexes(dry_run=args.dry_run), 'mode': 'dry-run' if args.dry_run else 'apply'}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == 'check':
        return check_indexes()
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
