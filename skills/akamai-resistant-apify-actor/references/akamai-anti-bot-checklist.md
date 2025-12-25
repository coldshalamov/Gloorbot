# Akamai Anti-Bot Checklist

Use this as a hard checklist for Akamai-class targets.

## Non-Negotiables
- Headful browser by default.
- Residential proxies with session locking.
- Unique browser fingerprints per session.
- Headers aligned to the fingerprint.

## Fingerprint Surface Areas
- Canvas noise injection.
- WebGL vendor and renderer randomization.
- AudioContext noise injection.
- Screen resolution and viewport variance.
- User agent rotation with realistic header sets.
- Locale and timezone rotation.

## Order of Operations
1) Apply stealth (if used).
2) Apply fingerprint injection (or Crawlee fingerprints).
3) Apply resource blocking last.

## Session Alignment
- One proxy session per browser context.
- One fingerprint per session.
- Rotate both on block or usage threshold.

## Known Limitations
- TLS/JA3 and HTTP2 fingerprints are hard to spoof outside JS/Crawlee tools.
- Success is probabilistic; no 100 percent unblockable design.

## Read Next
- `fingerprint-and-headers.md`
- `session-and-proxy-strategy.md`
- `verification-playbook.md`
