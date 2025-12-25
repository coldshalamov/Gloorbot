# Session and Proxy Strategy

Target a cheapest reliable profile: moderate session rotation, stable fingerprint per session, and low concurrency.

## SessionPool Tuning
- Rotate sessions based on maxUsageCount and maxErrorScore.
- Increase retries for blocked responses and rotate on repeated errors.

## Residential Proxy Persistence
- Residential proxy sessions are short-lived unless kept active.
- Keep the session alive with regular traffic if you need continuity.

## Alignment Rules
- One proxy session per browser context.
- One fingerprint per session (stable within the session).
- Rotate fingerprint only when the session rotates.
