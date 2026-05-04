#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Tuple

OWNER = 'lhx499598826'
REPO = 'openclaw_external_skills_library'
BRANCH = 'main'
REGISTRY_URL = f'https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/registry.json'
CONTENTS_API = f'https://api.github.com/repos/{OWNER}/{REPO}/contents'
WORKSPACE = Path('/home/liu/.openclaw/workspace')
SKILLS_DIR = WORKSPACE / 'skills'
CACHE_DIR = WORKSPACE / '.skillrouter-cache'
REGISTRY_CACHE = CACHE_DIR / 'registry.json'
MARKER = '.mounted-by-skillrouter'
TOPK_DEFAULT = 8

STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'how', 'i', 'in', 'is', 'it',
    'me', 'my', 'of', 'on', 'or', 'please', 'show', 'that', 'the', 'this', 'to', 'up', 'use', 'want', 'with'
}


def ensure_dirs() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)


def http_get(url: str, no_cache: bool = False) -> bytes:
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'skillrouter-v1'
    }
    if no_cache:
        headers.update({
            'Cache-Control': 'no-cache, no-store, max-age=0',
            'Pragma': 'no-cache'
        })
        sep = '&' if '?' in url else '?'
        url = f'{url}{sep}_ts={int(time.time())}&_nonce={hashlib.sha1(str(time.time_ns()).encode()).hexdigest()[:10]}'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_registry(force: bool = False) -> Dict[str, Any]:
    ensure_dirs()
    if REGISTRY_CACHE.exists() and not force:
        try:
            return json.loads(REGISTRY_CACHE.read_text())
        except Exception:
            pass
    data = http_get(REGISTRY_URL, no_cache=force)
    REGISTRY_CACHE.write_bytes(data)
    return json.loads(data.decode('utf-8'))


def normalize_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[-_/]+', ' ', s)
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def tokenize(s: str) -> List[str]:
    toks = [t for t in normalize_text(s).split() if t and t not in STOPWORDS]
    return toks


def build_entry_text(skill: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'key': skill.get('key', ''),
        'title': skill.get('title', ''),
        'shortDesc': skill.get('shortDesc', ''),
        'category': skill.get('category', ''),
        'tags': skill.get('tags', []) or [],
        'useCases': skill.get('useCases', []) or [],
    }


def score_skill(query: str, skill: Dict[str, Any]) -> Tuple[float, List[str]]:
    fields = build_entry_text(skill)
    q_norm = normalize_text(query)
    q_tokens = tokenize(query)
    score = 0.0
    reasons: List[str] = []

    key = normalize_text(fields['key'])
    title = normalize_text(fields['title'])
    short_desc = normalize_text(fields['shortDesc'])
    category = normalize_text(fields['category'])
    tags = [normalize_text(x) for x in fields['tags']]
    use_cases = [normalize_text(x) for x in fields['useCases']]

    if q_norm and q_norm == key:
        score += 20.0
        reasons.append(f'exact key match: {fields["key"]}')
    elif q_norm and q_norm in key:
        score += 12.0
        reasons.append(f'key substring match: {fields["key"]}')

    if q_norm and q_norm == title:
        score += 18.0
        reasons.append(f'exact title match: {fields["title"]}')
    elif q_norm and q_norm in title:
        score += 10.0
        reasons.append(f'title substring match: {fields["title"]}')

    if q_norm and q_norm in short_desc:
        score += 8.0
        reasons.append('shortDesc phrase match')

    if q_norm and q_norm in category:
        score += 3.0
        reasons.append(f'category phrase match: {fields["category"]}')

    for tag in tags:
        if q_norm and q_norm == tag:
            score += 9.0
            reasons.append(f'exact tag match: {tag}')
        elif q_norm and q_norm in tag:
            score += 5.0
            reasons.append(f'tag substring match: {tag}')

    for uc_raw, uc in zip(fields['useCases'], use_cases):
        if q_norm and q_norm in uc:
            score += 7.0
            reasons.append(f'useCase phrase match: {uc_raw}')

    token_hits = 0
    for token in q_tokens:
        if token == key:
            score += 6.0
            reasons.append(f'key token match: {token}')
            token_hits += 1
            continue
        if token in key:
            score += 2.5
            reasons.append(f'key partial token match: {token}')
            token_hits += 1
        if token in title:
            score += 2.5
            reasons.append(f'title token match: {token}')
            token_hits += 1
        if token in short_desc:
            score += 1.6
            reasons.append(f'shortDesc token match: {token}')
            token_hits += 1
        if token in category:
            score += 0.6
            reasons.append(f'category token match: {token}')
            token_hits += 1
        for tag in tags:
            if token in tag:
                score += 2.0
                reasons.append(f'tag token match: {token}')
                token_hits += 1
                break
        for uc_raw, uc in zip(fields['useCases'], use_cases):
            if token in uc:
                score += 1.4
                reasons.append(f'useCase token match: {token} -> {uc_raw}')
                token_hits += 1
                break

    if len(q_tokens) >= 2:
        hit_ratio = min(1.0, token_hits / max(1, len(q_tokens)))
        score += hit_ratio * 4.0
        if hit_ratio > 0:
            reasons.append(f'token coverage bonus: {hit_ratio:.2f}')

    uniq = []
    seen = set()
    for r in reasons:
        if r not in seen:
            uniq.append(r)
            seen.add(r)
    return score, uniq[:8]


def search_registry(query: str, topk: int) -> List[Dict[str, Any]]:
    reg = fetch_registry(force=False)
    skills = reg.get('skills', [])
    out = []
    for skill in skills:
        score, reasons = score_skill(query, skill)
        if score <= 0:
            continue
        item = {
            'key': skill.get('key'),
            'title': skill.get('title'),
            'path': skill.get('path'),
            'category': skill.get('category'),
            'shortDesc': skill.get('shortDesc'),
            'tags': skill.get('tags', []),
            'useCases': skill.get('useCases', []),
            'scores': {
                'lexical': round(score, 4),
                'final': round(score, 4),
            },
            'reasons': reasons,
        }
        out.append(item)
    out.sort(key=lambda x: (-x['scores']['final'], x['key']))
    return out[:topk]


def decide_rerank_mode(cands: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not cands:
        return {'status': 'no_match'}
    if len(cands) == 1:
        return {'status': 'auto_select', 'selected': cands[0]['key'], 'reason': 'only one candidate'}
    top1 = cands[0]['scores']['final']
    top2 = cands[1]['scores']['final']
    gap = top1 - top2
    if top1 >= 18 and gap >= 6:
        return {
            'status': 'auto_select',
            'selected': cands[0]['key'],
            'reason': f'top1 clearly ahead (gap={gap:.2f})'
        }
    if gap >= 8 and top1 < 10:
        return {
            'status': 'rerank_all',
            'reason': f'top1-top2 gap large but absolute confidence low (top1={top1:.2f}, gap={gap:.2f})'
        }
    return {
        'status': 'rerank_topk',
        'reason': f'need model rerank (top1={top1:.2f}, top2={top2:.2f}, gap={gap:.2f})'
    }


def load_registry_skills() -> List[Dict[str, Any]]:
    reg = fetch_registry(force=False)
    return reg.get('skills', [])


def find_skill(key: str) -> Dict[str, Any]:
    for skill in load_registry_skills():
        if skill.get('key') == key:
            return skill
    raise SystemExit(f'Skill not found in registry: {key}')


def github_contents(path: str) -> Any:
    encoded_path = '/'.join(urllib.parse.quote(part, safe='') for part in path.split('/'))
    url = f'{CONTENTS_API}/{encoded_path}?ref={urllib.parse.quote(BRANCH, safe="")}'
    data = http_get(url)
    return json.loads(data.decode('utf-8'))


def download_file(url: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlsplit(url)
    safe_path = urllib.parse.quote(parsed.path, safe='/%')
    safe_query = urllib.parse.urlencode(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True), doseq=True)
    safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, safe_path, safe_query, parsed.fragment))
    data = http_get(safe_url)
    dst.write_bytes(data)


def fetch_dir_recursive(repo_path: str, dst_root: Path) -> None:
    items = github_contents(repo_path)
    if isinstance(items, dict) and items.get('type') == 'file':
        download_file(items['download_url'], dst_root / Path(repo_path).name)
        return
    for item in items:
        t = item.get('type')
        name = item.get('name')
        item_path = item.get('path')
        if t == 'dir':
            fetch_dir_recursive(item_path, dst_root / name)
        elif t == 'file':
            download_file(item['download_url'], dst_root / name)


def mount_skill(key: str) -> Dict[str, Any]:
    ensure_dirs()
    skill = find_skill(key)
    dst = SKILLS_DIR / key
    if dst.exists():
        marker = dst / MARKER
        if marker.exists():
            shutil.rmtree(dst)
        else:
            raise SystemExit(f'Refusing to overwrite existing non-skillrouter skill: {dst}')
    dst.mkdir(parents=True, exist_ok=True)
    fetch_dir_recursive(skill['path'], dst)
    marker_payload = {
        'mountedBy': 'skillrouter',
        'repo': f'{OWNER}/{REPO}',
        'branch': BRANCH,
        'path': skill['path'],
        'mountedAt': int(time.time()),
    }
    (dst / MARKER).write_text(json.dumps(marker_payload, ensure_ascii=False, indent=2))
    return {
        'ok': True,
        'mounted': key,
        'destination': str(dst),
        'path': skill['path'],
        'note': 'Skill mounted. Start a new session or next eligible turn to ensure OpenClaw picks it up.'
    }


def unmount_skill(key: str) -> Dict[str, Any]:
    dst = SKILLS_DIR / key
    marker = dst / MARKER
    if not dst.exists():
        raise SystemExit(f'Skill directory not found: {dst}')
    if not marker.exists():
        raise SystemExit(f'Refusing to remove non-skillrouter skill: {dst}')
    shutil.rmtree(dst)
    return {'ok': True, 'unmounted': key}


def status() -> Dict[str, Any]:
    ensure_dirs()
    reg = fetch_registry(force=False)
    mounted = []
    for child in sorted(SKILLS_DIR.iterdir() if SKILLS_DIR.exists() else []):
        if child.is_dir() and (child / MARKER).exists():
            mounted.append(child.name)
    return {
        'repo': f'{OWNER}/{REPO}',
        'branch': BRANCH,
        'registryCache': str(REGISTRY_CACHE),
        'registryVersion': reg.get('version'),
        'generatedAt': reg.get('generatedAt'),
        'skillCount': len(reg.get('skills', [])),
        'mountedSkills': mounted,
    }


def cmd_status(_: argparse.Namespace) -> None:
    print(json.dumps(status(), ensure_ascii=False, indent=2))


def cmd_refresh(_: argparse.Namespace) -> None:
    reg = fetch_registry(force=True)
    print(json.dumps({
        'ok': True,
        'registryVersion': reg.get('version'),
        'generatedAt': reg.get('generatedAt'),
        'skillCount': len(reg.get('skills', [])),
        'cache': str(REGISTRY_CACHE),
    }, ensure_ascii=False, indent=2))


def cmd_search(args: argparse.Namespace) -> None:
    if args.mode != 'lexical':
        raise SystemExit(f"Search mode '{args.mode}' is reserved for future V2. V1 only supports lexical.")
    cands = search_registry(args.query, args.topk)
    decision = decide_rerank_mode(cands)
    print(json.dumps({
        'query': args.query,
        'mode': args.mode,
        'topk': args.topk,
        'decision': decision,
        'candidates': cands,
    }, ensure_ascii=False, indent=2))


def cmd_inspect(args: argparse.Namespace) -> None:
    skill = find_skill(args.skillKey)
    print(json.dumps(skill, ensure_ascii=False, indent=2))


def cmd_mount(args: argparse.Namespace) -> None:
    print(json.dumps(mount_skill(args.skillKey), ensure_ascii=False, indent=2))


def cmd_unmount(args: argparse.Namespace) -> None:
    print(json.dumps(unmount_skill(args.skillKey), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='skillrouter')
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('status')
    s.set_defaults(func=cmd_status)

    r = sub.add_parser('refresh-registry')
    r.set_defaults(func=cmd_refresh)

    se = sub.add_parser('search')
    se.add_argument('query')
    se.add_argument('--topk', type=int, default=TOPK_DEFAULT)
    se.add_argument('--mode', default='lexical', choices=['lexical', 'vector', 'hybrid'])
    se.set_defaults(func=cmd_search)

    i = sub.add_parser('inspect')
    i.add_argument('skillKey')
    i.set_defaults(func=cmd_inspect)

    m = sub.add_parser('mount')
    m.add_argument('skillKey')
    m.set_defaults(func=cmd_mount)

    u = sub.add_parser('unmount')
    u.add_argument('skillKey')
    u.set_defaults(func=cmd_unmount)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
