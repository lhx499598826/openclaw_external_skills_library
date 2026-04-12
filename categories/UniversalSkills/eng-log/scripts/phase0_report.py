#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import re
import shutil
import sys
from common import VAULT, parse_frontmatter, now_utc_iso, make_report_id, read_reports_list_yaml, write_reports_list_both

REPORTS_DIR = VAULT / 'reports'


def slugify(text: str) -> str:
    text = re.sub(r'[^A-Za-z0-9._ -]+', '', text).strip()
    text = re.sub(r'\s+', ' ', text)
    return text or 'untitled-report'


def infer_bucket(status: str, title: str) -> str:
    s = (status or '').lower()
    t = title.lower()
    if s in {'incident', 'failed', 'investigation'} or any(k in t for k in ['incident', 'failure', 'bug', 'debug']):
        return 'incidents'
    if s == 'design' or 'design' in t:
        return 'design'
    if any(k in t for k in ['update', 'upgrade', 'migration', 'deploy']):
        return 'updates'
    return 'daily'


def validate_report(content: str, meta: dict):
    errors = []
    required_fm = ['type', 'date', 'title', 'status']
    for key in required_fm:
        if not meta.get(key):
            errors.append(f'missing frontmatter field: {key}')
    required_sections = [
        '## Summary', '## Task Context', '## Participants and Responsibility Split',
        '## Execution Timeline', '## Observations and Evidence', '## Outcome and Current State', '## Traceability'
    ]
    for section in required_sections:
        if section not in content:
            errors.append(f'missing section: {section}')
    return errors


def ensure_report_id(content: str, meta: dict, path_hint: str):
    if meta.get('report_id'):
        return content, meta
    created_at = meta.get('created_at') or now_utc_iso()
    report_id = make_report_id(meta.get('date', ''), meta.get('title', ''), path_hint, created_at)
    insert = f"report_id: {report_id}\ncreated_at: {created_at}\n"
    content = content.replace('---\n', f'---\n{insert}', 1)
    meta['report_id'] = report_id
    meta['created_at'] = created_at
    return content, meta


def sync_reports_list(report_path: Path, meta: dict):
    data = read_reports_list_yaml()
    reports = data.get('reports', [])
    entry = {
        'report_id': meta.get('report_id'),
        'title': meta.get('title', report_path.stem),
        'date': meta.get('date', ''),
        'created_at': meta.get('created_at', ''),
        'system': meta.get('system', []) if isinstance(meta.get('system'), list) else [meta.get('system')] if meta.get('system') else [],
        'topic': meta.get('topic', []) if isinstance(meta.get('topic'), list) else [meta.get('topic')] if meta.get('topic') else [],
        'status': meta.get('status', ''),
        'severity': meta.get('severity', ''),
        'path': str(report_path.relative_to(VAULT)),
        'files_touched': meta.get('files_touched', []) if isinstance(meta.get('files_touched'), list) else [meta.get('files_touched')] if meta.get('files_touched') else [],
        'related_modules': meta.get('related_modules', []) if isinstance(meta.get('related_modules'), list) else [meta.get('related_modules')] if meta.get('related_modules') else [],
        'related_errors': meta.get('related_errors', []) if isinstance(meta.get('related_errors'), list) else [meta.get('related_errors')] if meta.get('related_errors') else [],
        'raw_refs': meta.get('raw_refs', []) if isinstance(meta.get('raw_refs'), list) else [meta.get('raw_refs')] if meta.get('raw_refs') else [],
    }
    reports = [r for r in reports if r.get('report_id') != entry['report_id']]
    reports.append(entry)
    reports.sort(key=lambda r: (r.get('created_at', ''), r.get('report_id', '')), reverse=True)
    data['reports'] = reports
    write_reports_list_both(data)


def command_ingest(src_path: Path):
    content = src_path.read_text(encoding='utf-8')
    meta = parse_frontmatter(content)
    errors = validate_report(content, meta)
    if errors:
        print(json.dumps({'ok': False, 'errors': errors}, ensure_ascii=False))
        return 1
    title = slugify(meta.get('title', src_path.stem))
    bucket = infer_bucket(meta.get('status', ''), title)
    dst = REPORTS_DIR / bucket / f'{title}.md'
    content, meta = ensure_report_id(content, meta, str(dst))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content, encoding='utf-8')
    sync_reports_list(dst, meta)
    print(json.dumps({'ok': True, 'action': 'ingest', 'saved': str(dst), 'report_id': meta.get('report_id')}, ensure_ascii=False))
    return 0


def command_amend(target_path: Path, source_path: Path):
    if not target_path.exists():
        print(json.dumps({'ok': False, 'errors': [f'target not found: {target_path}']}, ensure_ascii=False))
        return 1
    old_meta = parse_frontmatter(target_path.read_text(encoding='utf-8'))
    content = source_path.read_text(encoding='utf-8')
    meta = parse_frontmatter(content)
    errors = validate_report(content, meta)
    if errors:
        print(json.dumps({'ok': False, 'errors': errors}, ensure_ascii=False))
        return 1
    if old_meta.get('report_id') and not meta.get('report_id'):
        content = content.replace('---\n', f"---\nreport_id: {old_meta['report_id']}\ncreated_at: {old_meta.get('created_at', now_utc_iso())}\n", 1)
        meta = parse_frontmatter(content)
    title = slugify(meta.get('title', source_path.stem))
    bucket = infer_bucket(meta.get('status', ''), title)
    new_target = REPORTS_DIR / bucket / f'{title}.md'
    new_target.parent.mkdir(parents=True, exist_ok=True)
    new_target.write_text(content, encoding='utf-8')
    if new_target.resolve() != target_path.resolve() and target_path.exists():
        target_path.unlink()
    sync_reports_list(new_target, meta)
    print(json.dumps({'ok': True, 'action': 'amend', 'saved': str(new_target), 'report_id': meta.get('report_id')}, ensure_ascii=False))
    return 0


def command_check():
    report_files = sorted(REPORTS_DIR.rglob('*.md'))
    results = []
    failed = False
    for path in report_files:
        content = path.read_text(encoding='utf-8')
        meta = parse_frontmatter(content)
        errors = validate_report(content, meta)
        if not meta.get('report_id'):
            errors.append('missing frontmatter field: report_id')
        if not meta.get('created_at'):
            errors.append('missing frontmatter field: created_at')
        results.append({'path': str(path), 'ok': not errors, 'errors': errors})
        failed = failed or bool(errors)
    print(json.dumps({'ok': not failed, 'reports': results}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description='Phase 0 report helper')
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_ingest = sub.add_parser('ingest'); p_ingest.add_argument('source')
    p_amend = sub.add_parser('amend'); p_amend.add_argument('target'); p_amend.add_argument('source')
    sub.add_parser('check')
    args = parser.parse_args()
    if args.cmd == 'ingest':
        return command_ingest(Path(args.source).resolve())
    if args.cmd == 'amend':
        return command_amend(Path(args.target).resolve(), Path(args.source).resolve())
    if args.cmd == 'check':
        return command_check()
    return 1


if __name__ == '__main__':
    sys.exit(main())
