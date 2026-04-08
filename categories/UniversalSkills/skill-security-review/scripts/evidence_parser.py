from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

TRUSTED_REVIEW_HOSTS = {
    "github.com",
    "raw.githubusercontent.com",
    "codeload.github.com",
    "api.github.com",
    "registry.npmjs.org",
    "npmjs.com",
}

CODE_EXTS = {".py", ".js", ".ts", ".sh", ".mjs", ".cjs", ".bash"}
SENSITIVE_PATH_PATTERNS = [
    "/.ssh",
    ".ssh/",
    "/etc/",
    "/var/",
    "~/.gitconfig",
    ".env",
]
ENV_PATTERNS = [r"process\.env", r"os\.environ", r"os\.getenv\(", r"getenv\("]
URL_RE = re.compile(r"https?://[^\s)\]>\"']+")
COMMAND_HINTS = ["curl ", "wget ", "bash ", "sh ", "python ", "node ", "npm ", "pip ", "git "]
BENIGN_ENV_FILES = {"scripts/evidence_parser.py"}


def parse_evidence(root: str) -> Dict:
    base = Path(root)
    if not (base / "SKILL.md").exists():
        raise RuntimeError(f"target does not contain SKILL.md: {base}")

    files_scanned: List[str] = []
    commands_detected: List[str] = []
    urls_detected: List[str] = []
    env_access: List[str] = []
    sensitive_paths: List[str] = []
    declared_capabilities: List[str] = []
    observed_capabilities: List[str] = []

    skill_md = (base / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
    files_scanned.append("SKILL.md")
    declared_capabilities.extend(_extract_declared_capabilities(skill_md))
    urls_detected.extend(URL_RE.findall(skill_md))

    for path in base.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(base))
        if rel.startswith(".git/") or "/.git/" in rel:
            continue
        if path.name == "SKILL.md" or path.suffix in CODE_EXTS or path.name in {"package.json", "requirements.txt"}:
            files_scanned.append(rel)
            text = path.read_text(encoding="utf-8", errors="ignore")
            urls_detected.extend(URL_RE.findall(text))
            for patt in ENV_PATTERNS:
                if re.search(patt, text):
                    if rel not in BENIGN_ENV_FILES:
                        env_access.append(rel)
                    break
            for hint in COMMAND_HINTS:
                if hint in text:
                    commands_detected.append(f"{rel}: {hint.strip()}")
            for s in SENSITIVE_PATH_PATTERNS:
                if s in text:
                    sensitive_paths.append(rel)
            observed_capabilities.extend(_extract_observed_capabilities(text))
            if path.name == "package.json":
                _parse_package_json(text, observed_capabilities)

    trusted_urls, untrusted_urls = _split_urls(urls_detected)

    return {
        "files_scanned": sorted(set(files_scanned)),
        "commands_detected": sorted(set(commands_detected)),
        "urls_detected": sorted(set(urls_detected)),
        "trusted_urls": trusted_urls,
        "untrusted_urls": untrusted_urls,
        "env_access": sorted(set(env_access)),
        "sensitive_paths": sorted(set(sensitive_paths)),
        "declared_capabilities": sorted(set(filter(None, declared_capabilities))),
        "observed_capabilities": sorted(set(filter(None, observed_capabilities))),
    }


def _extract_declared_capabilities(text: str) -> List[str]:
    out = []
    lowered = text.lower()
    for kw in ["review", "audit", "scan", "analyze", "security", "search", "fetch", "edit", "deploy"]:
        if kw in lowered:
            out.append(kw)
    return out


def _extract_observed_capabilities(text: str) -> List[str]:
    lowered = text.lower()
    out = []
    mapping = {
        "network": ["http://", "https://", "requests.", "fetch(", "urllib"],
        "exec": ["subprocess", "os.system", "exec(", "eval(", "shell=True"],
        "write": ["write_text(", "open(", "fs.write", "appendfile"],
        "env-read": ["process.env", "os.environ", "os.getenv("],
        "git": ["git ", "github.com/"],
    }
    for cap, hints in mapping.items():
        if any(h.lower() in lowered for h in hints):
            out.append(cap)
    return out


def _split_urls(urls: List[str]) -> tuple[List[str], List[str]]:
    trusted: List[str] = []
    untrusted: List[str] = []
    for url in sorted(set(urls)):
        if "{" in url or "(" in url or "[" in url or "\\" in url:
            continue
        host = url.split("//", 1)[-1].split("/", 1)[0].lower()
        if host in TRUSTED_REVIEW_HOSTS:
            trusted.append(url)
        else:
            untrusted.append(url)
    return trusted, untrusted


def _parse_package_json(text: str, observed_capabilities: List[str]) -> None:
    try:
        data = json.loads(text)
    except Exception:
        return
    deps = {}
    deps.update(data.get("dependencies", {}))
    deps.update(data.get("devDependencies", {}))
    if deps:
        observed_capabilities.append("dependencies")
