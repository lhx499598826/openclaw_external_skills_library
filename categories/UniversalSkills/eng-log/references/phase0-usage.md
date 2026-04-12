# Phase 0 Usage

## Scope

Phase 0 supports:
- report ingest
- report amend
- reports-list maintenance
- validation checks

Phase 0 does not support formal indexes.

## Commands

### Ingest a generated report

```bash
python3 scripts/phase0_report.py ingest /path/to/report.md
```

### Amend an existing report with a revised markdown file

```bash
python3 scripts/phase0_report.py amend \
  vault/reports/design/example.md \
  /path/to/revised-report.md
```

### Validate current Phase 0 vault

```bash
python3 scripts/phase0_report.py check
```

## Minimum report requirements

The helper validates these frontmatter fields:
- type
- date
- title
- status

It also requires these sections to exist:
- Summary
- Task Context
- Participants and Responsibility Split
- Execution Timeline
- Observations and Evidence
- Outcome and Current State
- Traceability

## Notes

- Use the ENG-LOG v3 prompt to generate canonical reports before ingest.
- `reports-list.md` is updated automatically.
- If a title or status changes during amend, the helper rewrites path and list entry accordingly.
