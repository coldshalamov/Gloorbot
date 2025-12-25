# Blocking Detection and Recovery

Use these patterns to keep the actor alive under Akamai/WAF pressure.

## Detect Blocks
- "Access Denied" or known Akamai markers in HTML.
- Unusual redirects to home or challenge pages.
- Browser crash pages ("Aw, Snap"), timeouts, or empty results.

## Recovery Strategy
- Retry with exponential backoff.
- Rotate session and fingerprint on repeated errors.
- Reuse or rebuild browser context based on error count.
- Reduce concurrency when block rate increases.

## Session Rules
- Lock a proxy session to a single browser context.
- Retire a session after max usage or max error score.
- Keep fingerprints stable within a session; rotate only with session.

## Observability
- Log per-session fingerprint info, proxy session id, and errors.
- Record block rate and success rate by session.
