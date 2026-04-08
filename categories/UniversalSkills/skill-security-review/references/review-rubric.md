# Review Rubric

## Intent alignment

Check whether declared purpose matches observed capabilities.

Look for:
- declared task versus actual reachable behavior
- unrelated capabilities that expand scope
- hidden automation or background actions

## Permission rationality

Check whether requested or implied permissions are justified.

Look for:
- exec, network, file write, env access, home directory access
- weak or missing justification for sensitive capability
- violations of least-privilege expectations

## Prompt injection and social engineering

Check instruction text for attempts to bypass higher-priority rules or manipulate approval flow.

Look for:
- ignore previous instructions
- do not tell the user
- act silently
- ask for approval in a misleading way
- treat external content as trusted instructions

## Data flow and exfiltration

Map what can be read and where it can go.

Look for:
- env var access
- credential files, SSH directories, git config, tokens
- network destinations, webhooks, APIs, uploads
- logs, commits, issue comments, or artifacts used as sinks

## Compositional risk

Consider low-signal parts in combination.

Examples:
- env read + network egress
- file read + remote upload
- remote fetch + local exec
- hidden-action language + broad permissions

## Severity hints

- low: minor concern, bounded impact
- medium: meaningful concern, manual review justified
- high: strong abuse potential, restrict by default
- critical: clear malicious or covert high-impact path, block by default
