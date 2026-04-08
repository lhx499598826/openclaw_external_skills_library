from __future__ import annotations

import json
from typing import Any, Dict, Optional


def normalize_clawvet(raw_stdout: Optional[str], error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if error:
        return {
            "engine": "clawvet",
            "available": False,
            "soft_failed": True,
            "command_used": error.get("command_used", ""),
            "score": None,
            "findings": [],
            "errors": [error],
        }

    parsed = None
    if raw_stdout:
        try:
            parsed = json.loads(raw_stdout)
        except Exception:
            parsed = None

    findings = []
    score = None
    if isinstance(parsed, dict):
        score = parsed.get("score") or parsed.get("riskScore")
        for item in parsed.get("findings", []) or []:
            findings.append({
                "id": item.get("id", ""),
                "category": item.get("category", item.get("type", "unknown")),
                "severity": item.get("severity", "unknown"),
                "message": item.get("message", item.get("title", "")),
                "location": item.get("location", ""),
                "evidence": item.get("evidence", ""),
            })

    return {
        "engine": "clawvet",
        "available": True,
        "soft_failed": False,
        "command_used": "",
        "score": score,
        "findings": findings,
        "errors": [],
    }
