# Phase 3 Usage

## Scope

Phase 3 adds:
- feature indexes
- workflow indexes
- query router with intent routing and reports-list fallback

## Commands

### Build feature and workflow indexes

```bash
python3 scripts/phase3_router.py build
```

### Query the archive

```bash
python3 scripts/phase3_router.py query "how does the memory workflow work"
```

### Validate feature and workflow indexes

```bash
python3 scripts/phase3_router.py check
```

## Query behavior

- design/workflow style questions route to feature/workflow indexes first
- file/module questions route to component indexes
- config questions route to config indexes
- history/debug/event questions route to event indexes
- if there is no index hit, the router falls back to `reports-list.md`
