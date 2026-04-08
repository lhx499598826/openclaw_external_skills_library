from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

from target_loader import load_target
from evidence_parser import parse_evidence
from normalize_findings import normalize_clawvet
from render_report import render_json, render_summary


def run_clawvet(wrapper: Path, target_path: str) -> Dict:
    cmd = ["bash", str(wrapper), target_path, "--format", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as e:
        return normalize_clawvet(None, {
            "type": "scanner_invocation_failed",
            "message": str(e),
            "stderr": str(e),
            "exit_code": None,
            "command_used": " ".join(cmd),
        })

    if proc.returncode != 0:
        return normalize_clawvet(None, {
            "type": "scanner_invocation_failed",
            "message": "clawvet scan failed",
            "stderr": proc.stderr.strip(),
            "exit_code": proc.returncode,
            "command_used": " ".join(cmd),
        })

    data = normalize_clawvet(proc.stdout)
    data["command_used"] = " ".join(cmd)
    return data


def build_llm_review(evidence: Dict, scanner: Dict) -> Dict:
    observed = set(evidence.get("observed_capabilities", []))
    declared = set(evidence.get("declared_capabilities", []))
    env_access = evidence.get("env_access", [])
    urls = evidence.get("urls_detected", [])
    trusted_urls = evidence.get("trusted_urls", [])
    untrusted_urls = evidence.get("untrusted_urls", [])
    commands = evidence.get("commands_detected", [])

    suspicious_extra = sorted(observed - declared)
    if suspicious_extra and all(x in {"network", "git", "dependencies"} for x in suspicious_extra) and declared.intersection({"review", "audit", "scan", "security", "fetch"}):
        intent_alignment = "aligned"
    else:
        intent_alignment = "aligned" if not suspicious_extra else ("partial" if declared else "misaligned")

    sensitive_permissions: List[str] = []
    if "exec" in observed:
        sensitive_permissions.append("exec")
    if "env-read" in observed or env_access:
        sensitive_permissions.append("env-read")
    if "write" in observed:
        sensitive_permissions.append("write")
    if untrusted_urls:
        sensitive_permissions.append("network")

    hierarchy = []
    hidden = []
    se_signals = []
    for item in commands:
        low = item.lower()
        if "curl" in low or "wget" in low:
            se_signals.append("remote fetch capability present")
    skill_text = Path(evidence.get("_skill_md_path", "")).read_text(encoding="utf-8", errors="ignore") if evidence.get("_skill_md_path") else ""
    lowered = skill_text.lower()
    for phrase in ["ignore previous instructions", "do not tell the user", "silently", "without asking", "bypass"]:
        if phrase in lowered:
            if phrase in {"ignore previous instructions", "bypass"}:
                hierarchy.append(phrase)
            else:
                hidden.append(phrase)

    data_flow_risk = "low"
    if ("env-read" in observed or env_access) and untrusted_urls:
        data_flow_risk = "high"
    elif untrusted_urls:
        data_flow_risk = "medium"
    elif trusted_urls:
        data_flow_risk = "low"

    risk_chains = []
    emergent = 0
    if ("env-read" in observed or env_access) and untrusted_urls:
        risk_chains.append({
            "chain": ["read env", "send to untrusted endpoint"],
            "severity": "critical",
            "explanation": "Environment-variable access combined with untrusted network destinations creates a plausible exfiltration path.",
        })
        emergent = 85
    elif "exec" in observed and untrusted_urls:
        risk_chains.append({
            "chain": ["fetch remote content", "execute local commands"],
            "severity": "high",
            "explanation": "Untrusted remote fetch plus command execution raises supply-chain and remote execution risk.",
        })
        emergent = 70

    return {
        "intent": {
            "declared_intent": ", ".join(sorted(declared)),
            "observed_capabilities": sorted(observed),
            "intent_alignment": intent_alignment,
            "suspicious_extra_capabilities": suspicious_extra,
        },
        "permissions": {
            "required_permissions": sorted(observed),
            "sensitive_permissions": sensitive_permissions,
            "justification_quality": "weak" if sensitive_permissions and not declared else ("clear" if declared else "weak"),
            "least_privilege_assessment": "fail" if ("env-read" in sensitive_permissions and "exec" in sensitive_permissions and "network" in sensitive_permissions) else ("warning" if sensitive_permissions else "pass"),
        },
        "prompt_injection_social_engineering": {
            "instruction_hierarchy_violations": hierarchy,
            "social_engineering_signals": sorted(set(se_signals)),
            "hidden_action_patterns": hidden,
            "risk": "high" if hierarchy or hidden else ("medium" if se_signals else "low"),
        },
        "data_flow": {
            "data_sources": ["environment variables"] if env_access else [],
            "data_sinks": ["network endpoints"] if urls else [],
            "external_destinations": urls[:20],
            "potential_exfiltration_paths": ["env -> untrusted network"] if data_flow_risk == "high" else [],
            "risk": data_flow_risk,
        },
        "compositional_risk": {
            "risk_chains": risk_chains,
            "emergent_risk_score": emergent,
        },
    }


def decide(evidence: Dict, scanner: Dict, llm_review: Dict) -> Dict:
    reasons = []
    mitigations = []
    severity = "low"
    verdict = "allow"
    confidence = "high"

    if scanner.get("soft_failed"):
        confidence = "medium"
        reasons.append("Scanner unavailable; decision relies on static evidence and model review.")

    pi_risk = llm_review["prompt_injection_social_engineering"]["risk"]
    df_risk = llm_review["data_flow"]["risk"]
    lp = llm_review["permissions"]["least_privilege_assessment"]
    emergent = llm_review["compositional_risk"]["emergent_risk_score"]

    if pi_risk == "high":
        reasons.append("Instruction text contains hierarchy-bypass or hidden-action signals.")
    if df_risk == "high":
        reasons.append("Observed capabilities create a plausible exfiltration path.")
    if lp == "fail":
        reasons.append("Sensitive permissions appear broader than necessary.")
    if emergent >= 80:
        reasons.append("Combined signals create critical compositional risk.")

    if emergent >= 80 or (pi_risk == "high" and df_risk == "high"):
        verdict = "block"
        severity = "critical"
        mitigations.extend([
            "Do not install or run this skill in its current form.",
            "Remove covert actions, exfiltration paths, or hierarchy-bypass language.",
        ])
    elif lp == "fail" or df_risk == "high" or pi_risk == "high":
        verdict = "restrict"
        severity = "high"
        mitigations.extend([
            "Disable network access unless strictly required.",
            "Require explicit human approval before any exec-capable action.",
            "Remove environment-variable access unless clearly justified.",
        ])
    elif scanner.get("soft_failed") or llm_review["intent"]["intent_alignment"] != "aligned":
        verdict = "review"
        severity = "medium"
        mitigations.extend([
            "Perform manual review before installation.",
            "Clarify intended capabilities and permission boundaries.",
        ])
    else:
        verdict = "allow"
        severity = "low"
        mitigations.append("No immediate restriction required; keep normal review discipline.")

    if scanner.get("soft_failed") and verdict == "allow":
        verdict = "review"
        severity = "medium"

    return {
        "verdict": verdict,
        "severity": severity,
        "confidence": confidence,
        "reasons": reasons or ["No strong malicious, injection, or exfiltration signals were found."],
        "required_mitigations": mitigations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Review an OpenClaw/agent skill for security risk")
    parser.add_argument("target", help="Local skill directory or GitHub repository URL")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--summary", action="store_true", help="Output summary")
    parser.add_argument("--strict", action="store_true", help="Reserved for stricter policy")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    wrapper = base_dir / "clawvet_wrapper.sh"

    target_info = load_target(args.target)
    try:
        evidence = parse_evidence(target_info["local_path"])
        evidence["_skill_md_path"] = str(Path(target_info["local_path"]) / "SKILL.md")
        scanner = run_clawvet(wrapper, target_info["local_path"])
        llm_review = build_llm_review(evidence, scanner)
        decision = decide(evidence, scanner, llm_review)
        report = {
            "skill": {
                "name": Path(target_info["local_path"]).name,
                "path": target_info["local_path"],
                "source": target_info["resolved_source"],
                "source_type": target_info["source_type"],
                "version": None,
            },
            "evidence": {k: v for k, v in evidence.items() if not k.startswith("_")},
            "scanner": scanner,
            "llm_review": llm_review,
            "decision": decision,
        }
        if args.json or not args.summary:
            print(render_json(report))
        if args.summary:
            if args.json:
                print()
            print(render_summary(report))
    except RuntimeError as e:
        report = {
            "skill": {
                "name": Path(target_info["local_path"]).name if target_info.get("local_path") else args.target,
                "path": target_info.get("local_path"),
                "source": target_info.get("resolved_source", args.target),
                "source_type": target_info.get("source_type", "unknown"),
                "version": None,
            },
            "evidence": {},
            "scanner": {
                "engine": "clawvet",
                "available": False,
                "soft_failed": True,
                "command_used": "",
                "score": None,
                "findings": [],
                "errors": [{"type": "target_parse_failed", "message": str(e)}],
            },
            "llm_review": {},
            "decision": {
                "verdict": "review",
                "severity": "medium",
                "confidence": "low",
                "reasons": [str(e)],
                "required_mitigations": [
                    "Point the tool at a single skill folder containing SKILL.md.",
                    "If using GitHub, provide a repository that is itself a skill, not a multi-skill library root.",
                ],
            },
        }
        if args.json or not args.summary:
            print(render_json(report))
        if args.summary:
            if args.json:
                print()
            print(render_summary(report))
    finally:
        if target_info.get("cleanup_required"):
            shutil.rmtree(target_info["local_path"], ignore_errors=True)
            parent = Path(target_info["local_path"]).parent
            shutil.rmtree(parent, ignore_errors=True)


if __name__ == "__main__":
    main()
