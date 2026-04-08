from __future__ import annotations

import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict

GITHUB_RE = re.compile(r"^https://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?$")


def is_github_url(target: str) -> bool:
    return bool(GITHUB_RE.match(target.strip()))


def load_target(target: str) -> Dict:
    target = target.strip()
    if is_github_url(target):
        return _load_github_repo(target)
    return _load_local_path(target)


def _load_local_path(target: str) -> Dict:
    p = Path(target).expanduser().resolve()
    if not p.exists():
        raise RuntimeError(f"local target does not exist: {p}")
    if not p.is_dir():
        raise RuntimeError(f"local target is not a directory: {p}")
    return {
        "source_type": "local",
        "resolved_source": str(p),
        "local_path": str(p),
        "cleanup_required": False,
    }


def _load_github_repo(url: str) -> Dict:
    m = GITHUB_RE.match(url)
    if not m:
        raise RuntimeError(f"unsupported GitHub URL: {url}")
    owner, repo = m.group(1), m.group(2)
    tmpdir = Path(tempfile.mkdtemp(prefix="skill-security-review-"))
    last_error = None
    for branch in ("main", "master"):
        archive_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
        zip_path = tmpdir / f"{repo}-{branch}.zip"
        try:
            req = urllib.request.Request(archive_url, headers={"User-Agent": "skill-security-review"})
            with urllib.request.urlopen(req, timeout=30) as r, open(zip_path, "wb") as f:
                shutil.copyfileobj(r, f)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmpdir)
            roots = [p for p in tmpdir.iterdir() if p.is_dir() and p.name.startswith(f"{repo}-")]
            if not roots:
                raise RuntimeError("archive extracted but repository root was not found")
            root = roots[0]
            return {
                "source_type": "github",
                "resolved_source": url,
                "local_path": str(root.resolve()),
                "cleanup_required": True,
            }
        except Exception as e:
            last_error = e
    raise RuntimeError(f"failed to load GitHub repository {url}: {last_error}")
