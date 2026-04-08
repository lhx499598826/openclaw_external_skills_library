# Decision Policy

## Verdicts

### allow
Use when intent is aligned, permissions are proportionate, and no strong injection or exfiltration patterns appear.

### review
Use when evidence is incomplete, ambiguous, or moderately suspicious without a strong abuse chain.

### restrict
Use when permissions are excessive, data-flow impact is high, or risk is significant but not clearly malicious.

### block
Use when there is clear prompt injection, hidden malicious behavior, covert exfiltration, or a critical compositional chain.

## Confidence

- high: scanner succeeded and evidence is coherent
- medium: some uncertainty or scanner unavailable but evidence still substantial
- low: target incomplete, scanner unavailable, or evidence ambiguous

## Soft-fail policy

If `clawvet` is unavailable or fails:
- record the exact error
- continue static analysis and model review
- lower confidence by at least one level
- note that scanner-backed findings are unavailable
