from __future__ import annotations

import json
from typing import Dict


def render_json(report: Dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


def render_summary(report: Dict) -> str:
    decision = report["decision"]
    scanner = report["scanner"]
    lines = [
        f"Verdict: {decision['verdict']}",
        f"Severity: {decision['severity']}",
        f"Confidence: {decision['confidence']}",
        "",
        "Why:",
    ]
    for reason in decision.get("reasons", [])[:6]:
        lines.append(f"- {reason}")
    if decision.get("required_mitigations"):
        lines.extend(["", "Mitigations:"])
        for item in decision["required_mitigations"][:6]:
            lines.append(f"- {item}")
    lines.extend(["", "Scanner:"])
    status = "soft-failed" if scanner.get("soft_failed") else ("available" if scanner.get("available") else "unavailable")
    lines.append(f"- clawvet: {status}")
    if scanner.get("command_used"):
        lines.append(f"- command: {scanner['command_used']}")
    if scanner.get("errors"):
        lines.append(f"- note: {scanner['errors'][0].get('message', 'scanner error')}")
    return "\n".join(lines)
