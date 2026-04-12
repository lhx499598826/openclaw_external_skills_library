---
name: eng-log
description: Generate structured engineering reports and maintain a report-first retrieval wiki for OpenClaw work. Use when creating or amending engineering reports for debugging, config changes, deployment, migration, system design, concluded tests, or decision-bearing discussions, and when querying archived reports via reports-list during phase 0.
---

# eng-log

Generate canonical engineering reports, maintain a lightweight reports list, and support report-first retrieval.

## Current deployment phase

Phase 0 is active and validated.

Phase 1 is available when the user asks for indexed retrieval setup.

Phase 0 includes:
- generating reports with the ENG-LOG v3 prompt
- amending reports
- maintaining `vault/reports-list.md`
- manual/fallback retrieval through reports-list and report metadata

Phase 1 adds:
- event indexes
- component indexes
- candidate handling for below-threshold or uncertain components
- minimal canonical_name and aliases metadata

Phase 2 adds:
- config indexes
- config candidates
- minimal merge/rename state for canonicalization prep

Phase 3 adds:
- feature indexes
- workflow indexes
- query router with fallback to reports-list

Phase 4 adds:
- overview pages
- optional error index
- reindex tooling across lower layers

## Archive discipline

Respect these levels:

- L1, must write: debugging, fault investigation, config changes, deployment, migration, system design
- L2, optional: concluded tests, discussions with decisions
- L3, do not write: random attempts, chat, one-off failed trial and error, low-value temporary operations

If the material is L3, do not force a report.

## Core rules

- Report-first: formal retrieval starts from reports
- Reports record reality, retrieval layers consume reports
- If retrieval is weak, improve retrieval logic before changing the report format
- Only change report structure if missing information blocks engineering understanding
- Preserve exact commands, paths, keys, errors, modules, and other critical strings when available
- Keep minimal traceability refs in every report

## Files in this skill

- Prompt reference: `references/eng-log-prompt-v3.md`
- Phase 0 usage guide: `references/phase0-usage.md`
- Phase 1 usage guide: `references/phase1-usage.md`
- Phase 2 usage guide: `references/phase2-usage.md`
- Phase 3 usage guide: `references/phase3-usage.md`
- Phase 4 usage guide: `references/phase4-usage.md`
- Phase 0 vault root: `vault/`
- Reports list: `vault/reports-list.md`
- Phase 0 helper script: `scripts/phase0_report.py`
- Phase 1 helper script: `scripts/phase1_index.py`
- Phase 2 helper script: `scripts/phase2_config.py`
- Phase 3 helper script: `scripts/phase3_router.py`
- Phase 4 helper script: `scripts/phase4_maint.py`

## Phase 0 workflow

### Create report

1. Collect the source material the user wants archived.
2. Classify it against L1/L2/L3.
3. If it should be archived, use the prompt in `references/eng-log-prompt-v3.md` to generate a canonical markdown report.
4. Ingest it with `python3 scripts/phase0_report.py ingest /path/to/report.md`.
5. Confirm `vault/reports-list.md` was updated.
6. Keep traceability refs in the report.

### Amend report

1. Load the target report.
2. Apply the requested correction or append newly confirmed facts in a revised markdown file.
3. Preserve chronology and exact evidence.
4. Run `python3 scripts/phase0_report.py amend <existing-report> <revised-report>`.
5. Confirm the corresponding item in `vault/reports-list.md` was refreshed.

### Query in Phase 0

Use this order:
1. scan `vault/reports-list.md`
2. narrow candidate reports by metadata
3. read selected reports
4. return the closest original description, not just a polished summary

## Phase 1 workflow

### Build indexes

1. Ensure Phase 0 reports already exist in `vault/reports/...`.
2. Run `python3 scripts/phase1_index.py build`.
3. Create one event index per report.
4. Create formal component indexes only for components that meet the threshold.
5. Write below-threshold components to `vault/index/_candidates/`.

### Validate indexes

1. Run `python3 scripts/phase1_index.py check`.
2. Confirm event indexes, component indexes, and candidate files are structurally valid.

## Phase 2 workflow

### Build config indexes

1. Ensure Phase 0 reports exist and Phase 1 artifacts do not conflict.
2. Run `python3 scripts/phase2_config.py build`.
3. Create formal config indexes only when a config key meets threshold.
4. Write below-threshold config objects to candidate storage.

### Record merge or rename state

1. Run `python3 scripts/phase2_config.py merge <old_name> <canonical_name>` when a rename or merge decision is made.
2. Treat `vault/index/merge-map.json` as the minimal canonical mapping state for this phase.

### Validate config artifacts

1. Run `python3 scripts/phase2_config.py check`.
2. Confirm config indexes, config candidates, and merge map behavior are structurally valid.

## Phase 3 workflow

### Build feature and workflow indexes

1. Ensure Phase 0, Phase 1, and Phase 2 artifacts already exist.
2. Run `python3 scripts/phase3_router.py build`.
3. Create feature/workflow indexes from suitable reports.

### Query archive state

1. Run `python3 scripts/phase3_router.py query "<question>"`.
2. Route by intent to feature, workflow, component, config, or event indexes.
3. If no index hit exists, fall back to `vault/reports-list.md`.

### Validate feature/workflow artifacts

1. Run `python3 scripts/phase3_router.py check`.
2. Confirm feature and workflow indexes are structurally valid.

## Phase 4 workflow

### Build overview pages

1. Run `python3 scripts/phase4_maint.py overview`.
2. Generate human-readable map pages over reports and indexes.

### Build optional error indexes

1. Run `python3 scripts/phase4_maint.py errors`.
2. Create error indexes from `related_errors` metadata when present.

### Reindex all lower layers

1. Run `python3 scripts/phase4_maint.py reindex`.
2. Rebuild lower phases in order.
3. Refresh overview pages and error indexes.

### Validate Phase 4 artifacts

1. Run `python3 scripts/phase4_maint.py check`.
2. Confirm overview and error index structures are valid.

## Reports list format

Keep one bullet per report with at least:
- title
- date
- system
- topic
- status
- report path
- files_touched when present
- related_modules when present
- related_errors when present
- raw_refs when present

## Traceability minimum

Each report should keep a `Traceability` section with source type and raw refs such as file paths, message ids, terminal output paths, or external identifiers.

## Notes

- Email delivery is not archival state
- In Phase 0, favor correctness and clean report generation over automation breadth
- Before moving to Phase 1, verify that report generation and reports-list maintenance are stable
