#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import re
from datetime import datetime, timezone

VAULT = Path(__file__).resolve().parent.parent / 'vault'
REPORTS_LIST_YAML = VAULT / 'reports-list.yaml'


def now_utc_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def slug(text: str) -> str:
    text = text.lower().strip().replace('.', ' ')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text


def short_hash(*parts: str, n: int = 4) -> str:
    joined = '||'.join(parts)
    return hashlib.sha1(joined.encode('utf-8')).hexdigest()[:n]


def make_report_id(date_str: str, title: str, path_hint: str, created_at: str | None = None) -> str:
    ts = (created_at or now_utc_iso()).replace('-', '').replace(':', '').replace('T', '_').replace('Z', '')
    ts = ts[:15]
    return f"rpt_{ts}_{short_hash(date_str, title, path_hint)}"


def make_index_id(index_type: str, canonical_name: str) -> str:
    return f"idx_{index_type}_{slug(canonical_name)}_{short_hash(index_type, canonical_name)}"


def make_candidate_id(candidate_type: str, canonical_name: str, seen_at: str | None = None) -> str:
    ts = (seen_at or now_utc_iso()).replace('-', '').replace(':', '').replace('T', '').replace('Z', '')[:8]
    return f"cand_{candidate_type}_{ts}_{short_hash(candidate_type, canonical_name)}"


def parse_frontmatter(content: str):
    if not content.startswith('---\n'):
        return {}
    parts = content.split('\n---\n', 1)
    if len(parts) != 2:
        return {}
    fm = parts[0][4:]
    data = {}
    current_key = None
    for line in fm.splitlines():
        if not line.strip():
            continue
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*:', line):
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            if val:
                data[key] = val
                current_key = None
            else:
                data[key] = []
                current_key = key
        elif current_key and line.strip().startswith('- '):
            data[current_key].append(line.strip()[2:])
    return data


def dump_yaml_like(obj, indent=0):
    sp = '  ' * indent
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                out.append(f'{sp}{k}:')
                out.extend(dump_yaml_like(v, indent + 1))
            else:
                val = 'null' if v is None else str(v)
                out.append(f'{sp}{k}: {val}')
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                out.append(f'{sp}-')
                out.extend(dump_yaml_like(item, indent + 1))
            else:
                out.append(f'{sp}- {item}')
    return out


def write_reports_list_yaml(data):
    REPORTS_LIST_YAML.parent.mkdir(parents=True, exist_ok=True)
    REPORTS_LIST_YAML.write_text('\n'.join(dump_yaml_like(data)) + '\n', encoding='utf-8')


def read_reports_list_yaml():
    if not REPORTS_LIST_YAML.exists():
        return {'type': 'reports_list', 'version': 1, 'sorted_by': ['created_at_desc', 'report_id_desc'], 'reports': []}
    # simple parser via json fallback stored in commentless yaml-like structure is not robust, so use line-based assumptions
    # for this migration phase, prefer loading cached json sidecar when present
    sidecar = REPORTS_LIST_YAML.with_suffix('.json')
    if sidecar.exists():
        return json.loads(sidecar.read_text(encoding='utf-8'))
    return {'type': 'reports_list', 'version': 1, 'sorted_by': ['created_at_desc', 'report_id_desc'], 'reports': []}


def write_reports_list_both(data):
    write_reports_list_yaml(data)
    REPORTS_LIST_YAML.with_suffix('.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
