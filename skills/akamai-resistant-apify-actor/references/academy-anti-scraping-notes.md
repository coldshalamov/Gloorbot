# Academy Anti-Scraping Notes

## Four Detection Axes
- IP reputation and rate limiting.
- Headers, TLS, and browser fingerprint.
- What endpoints are scraped (HTML vs API).
- Behavior and timing patterns.

## Practical Mitigations
- Use high-quality residential proxies.
- Align headers to the active fingerprint.
- Use a real browser for challenges when needed.
- Rotate sessions and increase retries.
- Lower concurrency and add human-like jitter.
- Prefer less-protected APIs when possible.

## Reality Check
- There is no single silver bullet.
- Some requests will be blocked; rely on retries.
- Success depends on target configuration and changes.
