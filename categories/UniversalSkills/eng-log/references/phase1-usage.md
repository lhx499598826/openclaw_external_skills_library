# Phase 1 Usage

## Scope

Phase 1 adds:
- event index generation
- component index generation
- candidate handling for uncertain or below-threshold components
- minimal canonical_name and aliases frontmatter

## Commands

### Build Phase 1 indexes from current reports

```bash
python3 scripts/phase1_index.py build
```

### Validate generated indexes and candidates

```bash
python3 scripts/phase1_index.py check
```

## Current promotion rule

- event: create directly from each report
- component: create formal index only when the component appears in at least 2 reports
- otherwise store it under `vault/index/_candidates/`

## Notes

- This phase does not yet include config, feature/workflow, or query router
- Candidate files are JSON to keep the state explicit and easy to inspect
