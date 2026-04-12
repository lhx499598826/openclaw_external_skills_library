---
report_id: rpt_20260412_174731_7ddf
created_at: 2026-04-12T17:47:31Z
type: report
date: 2026-04-12
title: eng-log skill architecture reference 2026-04-12
system:
  - OpenClaw
  - eng-log
topic:
  - architecture
  - retrieval wiki
  - design
status: design
severity: medium
source_kind:
  - file
  - design
files_touched:
  - skills/eng-log-clean/SKILL.md
  - skills/eng-log-clean/scripts/common.py
  - skills/eng-log-clean/scripts/phase0_report.py
  - skills/eng-log-clean/scripts/phase1_index.py
  - skills/eng-log-clean/scripts/phase2_config.py
  - skills/eng-log-clean/scripts/phase3_router.py
  - skills/eng-log-clean/scripts/phase4_maint.py
related_modules:
  - common.py
  - phase0_report.py
  - phase1_index.py
  - phase2_config.py
  - phase3_router.py
  - phase4_maint.py
raw_refs:
  - local architecture reference
---

## Summary
- Objective was to document the final architecture of the eng-log skill.
- The system uses a report-first vault with layered indexes and maintenance tooling.
- Reports are the formal fact layer, while indexes and overview pages are retrieval layers.
- Current status is design reference for future maintenance.

## Task Context
Future use of the skill needs a stable internal description of how the pieces fit together. This report exists as an internal architecture reference for later operators and future updates.

## Participants and Responsibility Split
### User Actions
- Requested a future-readable description of the skill itself.

### OpenClaw Actions
- Produced the architecture description.

### Other System Actions
- Local filesystem stores the vault and helper scripts.

## Environment and Operational Snapshot
### Host / Runtime
- Linux host
- File-based vault design

## Execution Timeline
1. Report layer was defined around canonical engineering records.
2. Reports-list was normalized into a fixed YAML structure.
3. Index layers were added in stages: event, component, config, feature, workflow, error.
4. Query routing and maintenance layers were added after the lower layers were validated.

## Files, Code, and Configuration Involved
### Files Touched
- skills/eng-log-clean/scripts/common.py
- skills/eng-log-clean/scripts/phase0_report.py
- skills/eng-log-clean/scripts/phase1_index.py
- skills/eng-log-clean/scripts/phase2_config.py
- skills/eng-log-clean/scripts/phase3_router.py
- skills/eng-log-clean/scripts/phase4_maint.py

### Relevant Code or Config Snippets
```text
vault/
  reports/
  index/
  wiki/overview/
  reports-list.yaml
```

## Observations and Evidence
- The vault is local and markdown-based.
- Obsidian compatibility is optional, not required.
- Helper scripts separate concerns by phase.

## Analysis and Reasoning
The architecture is intentionally layered so the report layer remains the source of truth. Retrieval layers accelerate lookup but do not replace the factual record.

## Outcome and Current State
🧭 Design only
This report is the architecture reference for future work on the skill.

## Traceability
- source:
  - local file
- raw_ref:
  - skills/eng-log-clean

## Architecture Sketch
```text
[Canonical Reports]
      ↓
[reports-list.yaml]
      ↓
[event/component/config/feature/workflow/error indexes]
      ↓
[query router + overview + reindex]
```

## Engineering Notes
- report-first is a hard rule
- indexes are rebuildable
- reports-list is fixed-structure metadata
