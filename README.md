# openclaw_external_skills_library

External skills library for OpenClaw, intended for **lazy mounting** into an agent workspace only when needed.

## Layout

- `categories/<category>/<skillKey>/SKILL.md` — skill folders (AgentSkills format)
- `registry.json` — compact index used for fast search/recall
- `registry.schema.json` — JSON schema for `registry.json`

## Adding a skill

1. Create a folder: `categories/<category>/<skillKey>/`
2. Add `SKILL.md` (AgentSkills-compatible)
3. Add any supporting scripts/files under that folder
4. Add an entry to `registry.json`

## Registry fields (per skill)

- `key`: stable id, also used as the mounted folder name
- `category`: e.g. `trading`, `research`
- `path`: repo-relative path to the skill folder
- `title`: human name
- `shortDesc`: 1-sentence description
- `tags`: keywords
- `useCases`: 3-8 natural-language queries that this skill should match

## Notes

This repo by itself does **not** make skills "registered" in OpenClaw.
A runtime/registry skill must mount a chosen skill into `<workspace>/skills/` to make it eligible.
