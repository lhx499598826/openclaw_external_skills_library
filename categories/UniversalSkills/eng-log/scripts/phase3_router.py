#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import re
from common import VAULT, parse_frontmatter, slug, make_index_id, read_reports_list_yaml

INDEX_DIR = VAULT / 'index'
FEATURES_DIR = INDEX_DIR / 'features'
WORKFLOWS_DIR = INDEX_DIR / 'workflows'
EVENTS_DIR = INDEX_DIR / 'events'
COMPONENTS_DIR = INDEX_DIR / 'components'
CONFIGS_DIR = INDEX_DIR / 'configs'
REPORTS_LIST_YAML = VAULT / 'reports-list.yaml'


def read_file(path: Path):
    return path.read_text(encoding='utf-8')


def report_entries():
    return read_reports_list_yaml().get('reports', [])


def classify_report(meta: dict, content: str):
    title = meta.get('title', '').lower()
    text = (title + '\n' + content).lower()
    is_workflow = any(k in text for k in ['workflow', 'process', 'migration', 'deploy', 'update'])
    is_feature = any(k in text for k in ['memory', 'retrieval', 'feature', 'design'])
    return is_feature, is_workflow


def write_index(path: Path, index_type: str, canonical: str, alias: str, report_id: str, report_path: str, goal: str, how: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    index_id = make_index_id(index_type, canonical)
    content = f"""---
index_id: {index_id}
type: index
index_type: {index_type}
canonical_name: {canonical}
aliases:
  - {alias}
status: active
source_reports:
  - {report_id}
source_paths:
  - {report_path}
---

# {canonical}

## Goal
{goal}

## How It Works
{how}

## Main Components

## Related Configs

## Related Reports
- [[{report_path}]]

## Operational Notes
Auto-generated in Phase 3.

## Notes
Inspect linked reports for the closest original description.
"""
    path.write_text(content, encoding='utf-8')
    return path


def build_indexes(dry_run=False):
    results = {'features_to_create': [], 'workflows_to_create': []}
    for entry in report_entries():
        report = VAULT / entry['path']
        content = read_file(report)
        meta = parse_frontmatter(content)
        title = meta.get('title', report.stem)
        is_feature, is_workflow = classify_report(meta, content)
        if is_feature:
            canonical = f'feature-{slug(title)}'
            if dry_run:
                results['features_to_create'].append(canonical)
            else:
                path = FEATURES_DIR / f'{canonical}.md'
                write_index(path, 'feature', canonical, title, entry['report_id'], entry['path'], f'Derived from {title}', 'Use related reports and lower layers for factual details.')
                results['features_to_create'].append(str(path))
        if is_workflow:
            canonical = f'workflow-{slug(title)}'
            if dry_run:
                results['workflows_to_create'].append(canonical)
            else:
                path = WORKFLOWS_DIR / f'{canonical}.md'
                write_index(path, 'workflow', canonical, title, entry['report_id'], entry['path'], f'Derived from {title}', 'Use related reports and lower layers for factual details.')
                results['workflows_to_create'].append(str(path))
    return results


def query_tokens(query: str):
    return [t for t in re.split(r'[^a-zA-Z0-9_.-]+', query.lower()) if t]


def score_text(text: str, tokens):
    lower = text.lower()
    return sum(1 for t in tokens if t in lower)


def search_index_dir(dir_path: Path, query: str):
    hits = []
    tokens = query_tokens(query)
    for path in sorted(dir_path.glob('*.md')):
        content = read_file(path)
        score = score_text(content, tokens)
        if score > 0:
            hits.append({'path': str(path), 'type': dir_path.name, 'score': score})
    hits.sort(key=lambda x: (-x['score'], x['path']))
    return hits


def fallback_reports(query: str):
    tokens = query_tokens(query)
    hits = []
    for entry in report_entries():
        text = json.dumps(entry, ensure_ascii=False)
        score = score_text(text, tokens)
        if score > 0:
            hits.append({'report_id': entry['report_id'], 'path': entry['path'], 'score': score, 'title': entry['title']})
    hits.sort(key=lambda x: -x['score'])
    return hits


def route_query(query: str):
    q = query.lower()
    intents = []
    if any(k in q for k in ['design', 'how it works', 'how works', 'feature', 'workflow', 'process']): intents.extend(['features', 'workflows'])
    if any(k in q for k in ['file', 'path', 'module', 'service', 'component']): intents.append('components')
    if any(k in q for k in ['config', 'compatibility', 'update impact', 'memory.backend', 'setting']): intents.append('configs')
    if any(k in q for k in ['what happened', 'history', 'incident', 'debug', 'event', 'before']): intents.append('events')
    if not intents: intents = ['reports-list']
    intents = list(dict.fromkeys(intents))
    hits = []
    for intent in intents:
        if intent == 'features': hits.extend(search_index_dir(FEATURES_DIR, query))
        elif intent == 'workflows': hits.extend(search_index_dir(WORKFLOWS_DIR, query))
        elif intent == 'components': hits.extend(search_index_dir(COMPONENTS_DIR, query))
        elif intent == 'configs': hits.extend(search_index_dir(CONFIGS_DIR, query))
        elif intent == 'events': hits.extend(search_index_dir(EVENTS_DIR, query))
    fallback = []
    if not hits: fallback = fallback_reports(query)
    print(json.dumps({'query': query, 'intents': intents, 'hits': hits, 'fallback_reports': fallback, 'status': 'index_hit' if hits else ('fallback_hit' if fallback else 'no_hit')}, ensure_ascii=False, indent=2))
    return 0


def check():
    failed = False
    results = {'features': [], 'workflows': []}
    for path in sorted(FEATURES_DIR.glob('*.md')):
        c = read_file(path)
        ok = 'index_id:' in c and 'canonical_name:' in c and '## Related Reports' in c
        results['features'].append({'path': str(path), 'ok': ok}); failed = failed or not ok
    for path in sorted(WORKFLOWS_DIR.glob('*.md')):
        c = read_file(path)
        ok = 'index_id:' in c and 'canonical_name:' in c and '## Related Reports' in c
        results['workflows'].append({'path': str(path), 'ok': ok}); failed = failed or not ok
    print(json.dumps({'ok': not failed, 'results': results}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_build = sub.add_parser('build'); p_build.add_argument('--dry-run', action='store_true')
    p_query = sub.add_parser('query'); p_query.add_argument('text')
    sub.add_parser('check')
    args = parser.parse_args()
    if args.cmd == 'build': print(json.dumps({'ok': True, 'result': build_indexes(dry_run=args.dry_run), 'mode': 'dry-run' if args.dry_run else 'apply'}, ensure_ascii=False, indent=2)); return 0
    if args.cmd == 'query': return route_query(args.text)
    if args.cmd == 'check': return check()
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
