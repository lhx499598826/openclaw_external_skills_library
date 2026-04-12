---
report_id: rpt_20260412_174731_fc5b
created_at: 2026-04-12T17:47:31Z
type: report
date: 2026-04-12
title: eng-log skill usage reference 2026-04-12
system:
  - OpenClaw
  - eng-log
topic:
  - usage
  - operations
  - workflow
status: design
severity: low
source_kind:
  - file
files_touched:
  - skills/eng-log-clean/references/phase0-usage.md
  - skills/eng-log-clean/references/phase1-usage.md
  - skills/eng-log-clean/references/phase2-usage.md
  - skills/eng-log-clean/references/phase3-usage.md
  - skills/eng-log-clean/references/phase4-usage.md
related_modules:
  - phase0_report.py
  - phase1_index.py
  - phase2_config.py
  - phase3_router.py
  - phase4_maint.py
raw_refs:
  - local usage reference
---

## Summary
- Objective was to capture detailed usage guidance for future operation of eng-log.
- The skill is operated in phases but can also be maintained holistically after full deployment.
- Core actions are report ingest, amend, indexing, query, and reindex.
- Current status is design/operations reference.

## Task Context
The skill now exists and needs an operational reference so later use does not depend on rereading the entire build conversation.

## Participants and Responsibility Split
### User Actions
- Requested future-readable usage documentation.

### OpenClaw Actions
- Produced the usage reference.

### Other System Actions
- Local filesystem stores usage references.

## Environment and Operational Snapshot
### Host / Runtime
- Linux host
- OpenClaw workspace

## Execution Timeline
1. Phase usage notes were created during implementation.
2. A consolidated usage reference was produced afterward.

## Inputs, Data Flow, and Intermediate State
### Expected Flow
source material -> canonical report -> reports-list -> indexes -> query/reindex

## Observations and Evidence
- `phase0_report.py` handles report ingest/amend/check.
- `phase1_index.py` handles event/component build.
- `phase2_config.py` handles config build and merge state.
- `phase3_router.py` handles feature/workflow build and querying.
- `phase4_maint.py` handles overview, error indexes, and reindex.

## Outcome and Current State
🧭 Design only
This report acts as the usage reference for future operators.

## Follow-up
- Keep this reference updated if commands or storage layout change.

## Traceability
- source:
  - local file
- raw_ref:
  - skills/eng-log-clean/references

## Engineering Notes
- use L1/L2/L3 archive discipline before report generation
- prefer dry-run for rebuilds before applying them in bulk
- keep report content factual and do not warp it to satisfy indexes
