# Verification Playbook

Use this to validate the actor before scaling.

## Fingerprint Checks
- Visit fingerprint test pages and confirm unique fingerprints per session.
- Log fingerprint metadata per session (UA, locale, timezone, viewport).

## Session Alignment Checks
- Log proxy session id and fingerprint id together.
- Confirm no shared fingerprint across different proxy sessions.

## Block-Rate Thresholds
- Track block rate per 100 requests.
- If block rate rises, reduce concurrency or rotate sessions more often.

## Cost Checks
- Record compute hours and proxy bandwidth.
- Validate that browser pooling reduces total browser launches.
