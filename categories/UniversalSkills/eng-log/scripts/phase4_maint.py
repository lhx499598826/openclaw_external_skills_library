#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import subprocess
import re
from common import VAULT, parse_frontmatter, read_reports_list_yaml

INDEX_DIR = VAULT / 'index'
WIKI_DIR = VAULT / 'wiki' / 'overview'
EVENTS_DIR = INDEX_DIR / 'events'
COMPONENTS_DIR = INDEX_DIR / 'components'
CONFIGS_DIR = INDEX_DIR / 'configs'
FEATURES_DIR = INDEX_DIR / 'features'
WORKFLOWS_DIR = INDEX_DIR / 'workflows'
ERRORS_DIR = INDEX_DIR / 'errors'
REPORTS_DIR = VAULT / 'reports'


def slug(text: str) -> str:
    text = text.lower().strip().replace('.', ' ')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text


def write_overview(dry_run=False):
    pages = {
        'openclaw-overview.md': '# OpenClaw 总览\n\n## Reports\n',
        'configuration-update-impact-overview.md': '# 配置与更新影响总览\n\n## Config Indexes\n',
        'migration-deployment-overview.md': '# 迁移与部署总览\n\n## Workflow Indexes\n',
        'common-components-overview.md': '# 常用组件与路径总览\n\n## Component Indexes\n',
        'workflow-overview.md': '# 工作流总览\n\n## Workflow Indexes\n',
    }
    report_lines = [f"- [[{e['path']}]]" for e in read_reports_list_yaml().get('reports', [])]
    config_lines = [f'- [[index/configs/{p.name}]]' for p in sorted(CONFIGS_DIR.glob('*.md'))]
    workflow_lines = [f'- [[index/workflows/{p.name}]]' for p in sorted(WORKFLOWS_DIR.glob('*.md'))]
    component_lines = [f'- [[index/components/{p.name}]]' for p in sorted(COMPONENTS_DIR.glob('*.md'))]
    feature_lines = [f'- [[index/features/{p.name}]]' for p in sorted(FEATURES_DIR.glob('*.md'))]
    planned = []
    for name, header in pages.items():
        body = header
        if name == 'openclaw-overview.md': body += '\n'.join(report_lines + feature_lines) + '\n'
        elif name == 'configuration-update-impact-overview.md': body += '\n'.join(config_lines) + '\n'
        elif name == 'migration-deployment-overview.md': body += '\n'.join(workflow_lines) + '\n'
        elif name == 'common-components-overview.md': body += '\n'.join(component_lines) + '\n'
        elif name == 'workflow-overview.md': body += '\n'.join(workflow_lines) + '\n'
        planned.append({'path': str(WIKI_DIR / name), 'content_preview': body[:120]})
        if not dry_run:
            WIKI_DIR.mkdir(parents=True, exist_ok=True)
            (WIKI_DIR / name).write_text(body, encoding='utf-8')
    return planned


def write_error_indexes(dry_run=False):
    found = {}
    for entry in read_reports_list_yaml().get('reports', []):
        report = VAULT / entry['path']
        meta = parse_frontmatter(report.read_text(encoding='utf-8'))
        errors = meta.get('related_errors', [])
        if isinstance(errors, str): errors = [errors]
        for err in errors:
            if err: found.setdefault(err, []).append((entry['report_id'], entry['path']))
    planned = []
    for err, reports in found.items():
        canonical = f'error-{slug(err)}'
        path = ERRORS_DIR / f'{canonical}.md'
        planned.append({'path': str(path), 'error': err})
        if not dry_run:
            ERRORS_DIR.mkdir(parents=True, exist_ok=True)
            content = f"""---
index_id: idx_error_{slug(err)}
type: index
index_type: error
canonical_name: {canonical}
aliases:
  - {err}
status: active
source_reports:
"""
            for rid, _ in reports: content += f'  - {rid}\n'
            content += 'source_paths:\n'
            for _, rp in reports: content += f'  - {rp}\n'
            content += f"""---

# {canonical}

## Summary
Derived from related_errors metadata.

## Related Reports
"""
            for _, rp in reports: content += f'- [[{rp}]]\n'
            content += '\n## Notes\nPhase 4 optional error index.\n'
            path.write_text(content, encoding='utf-8')
    return planned


def run(cmd, dry_run=False):
    cmd = [c for c in cmd if c]
    if dry_run:
        return {'cmd': ' '.join(cmd), 'mode': 'dry-run'}
    proc = subprocess.run(cmd, cwd=Path(__file__).resolve().parent.parent, capture_output=True, text=True)
    return {'cmd': ' '.join(cmd), 'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}


def reindex_all(dry_run=False):
    return {
        'commands': [
            run(['python3', 'scripts/phase1_index.py', 'build', '--dry-run' if dry_run else None], dry_run=dry_run),
            run(['python3', 'scripts/phase2_config.py', 'build', '--dry-run' if dry_run else None], dry_run=dry_run),
            run(['python3', 'scripts/phase3_router.py', 'build', '--dry-run' if dry_run else None], dry_run=dry_run),
        ],
        'overview': write_overview(dry_run=dry_run),
        'errors': write_error_indexes(dry_run=dry_run)
    }


def check():
    failed = False
    results = {'overview': [], 'errors': []}
    for path in sorted(WIKI_DIR.glob('*.md')):
        content = path.read_text(encoding='utf-8')
        ok = content.startswith('# ')
        results['overview'].append({'path': str(path), 'ok': ok})
        failed = failed or not ok
    for path in sorted(ERRORS_DIR.glob('*.md')):
        content = path.read_text(encoding='utf-8')
        ok = 'canonical_name:' in content and '## Related Reports' in content
        results['errors'].append({'path': str(path), 'ok': ok})
        failed = failed or not ok
    print(json.dumps({'ok': not failed, 'results': results}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_over = sub.add_parser('overview'); p_over.add_argument('--dry-run', action='store_true')
    p_err = sub.add_parser('errors'); p_err.add_argument('--dry-run', action='store_true')
    p_re = sub.add_parser('reindex'); p_re.add_argument('--dry-run', action='store_true')
    sub.add_parser('check')
    args = parser.parse_args()
    if args.cmd == 'overview': print(json.dumps({'ok': True, 'overview': write_overview(dry_run=args.dry_run), 'mode': 'dry-run' if args.dry_run else 'apply'}, ensure_ascii=False, indent=2)); return 0
    if args.cmd == 'errors': print(json.dumps({'ok': True, 'errors': write_error_indexes(dry_run=args.dry_run), 'mode': 'dry-run' if args.dry_run else 'apply'}, ensure_ascii=False, indent=2)); return 0
    if args.cmd == 'reindex': print(json.dumps({'ok': True, 'result': reindex_all(dry_run=args.dry_run), 'mode': 'dry-run' if args.dry_run else 'apply'}, ensure_ascii=False, indent=2)); return 0
    if args.cmd == 'check': return check()
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
