# Fingerprints and Headers (Cheapest Reliable)

Use Crawlee's built-in fingerprinting and header generation whenever possible. Avoid manual UA/header overrides unless they are generated to match the active fingerprint.

## Defaults to Keep
- Crawlee/Playwright fingerprinting enabled (do not disable useFingerprints).
- Let Crawlee generate realistic headers that align with the fingerprint.

## When to Customize
- Only customize UA/headers if you use the same fingerprint source to generate them.
- If you override headers manually, you must keep them consistent across a session.

## Practical Notes
- Fingerprints must be stable within a session and change only when the session rotates.
- Avoid mixing fingerprints across parallel contexts using the same proxy session.
