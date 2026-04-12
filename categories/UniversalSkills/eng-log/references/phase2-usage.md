# Phase 2 Usage

## Scope

Phase 2 adds:
- config index generation
- config candidates below threshold
- minimal merge/rename state via `vault/index/merge-map.json`

## Commands

### Build config indexes from current reports

```bash
python3 scripts/phase2_config.py build
```

### Record a merge or rename mapping

```bash
python3 scripts/phase2_config.py merge <old_name> <canonical_name>
```

### Validate config indexes and config candidates

```bash
python3 scripts/phase2_config.py check
```

## Current promotion rule

- config: create formal index only when the same config key appears in at least 2 reports
- otherwise write it to candidate storage

## Notes

- This phase does not yet implement feature/workflow or query router
- Merge state is intentionally simple in this phase and is meant to prepare for later reindex work
