# Phase 4 Usage

## Scope

Phase 4 adds:
- overview pages
- optional error indexes from report metadata
- a reindex command that rebuilds lower layers and refreshes overview/error artifacts

## Commands

### Build overview pages

```bash
python3 scripts/phase4_maint.py overview
```

### Build optional error indexes

```bash
python3 scripts/phase4_maint.py errors
```

### Rebuild all lower layers and refresh Phase 4 outputs

```bash
python3 scripts/phase4_maint.py reindex
```

### Validate Phase 4 outputs

```bash
python3 scripts/phase4_maint.py check
```

## Notes

- Error indexes depend on `related_errors` metadata in reports
- Reindex is intentionally simple in this version and runs the lower-phase build commands in order
