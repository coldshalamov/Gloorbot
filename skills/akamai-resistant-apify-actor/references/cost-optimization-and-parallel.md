# Cost Optimization and Parallelism

Goal: cheapest reliable throughput without triggering Akamai correlation.

## Browser Pooling Pattern
- One browser per store or per proxy session.
- Reuse the browser across all pages for that unit.
- Create a small number of concurrent pages per browser (2-4).

## Why This Works
- Fewer browser launches reduce CPU and memory cost.
- Session locking keeps fingerprints consistent per store.
- Parallel tabs provide throughput without creating duplicate fingerprints.

## Bandwidth and Proxy Cost
- Block images, media, fonts when possible to reduce proxy bandwidth.
- Avoid full-page screenshots unless needed for debugging.

## Tuning Knobs
- CONCURRENT_PAGES_PER_BROWSER: start 2-4; reduce if blocks rise.
- maxConcurrency: keep modest to avoid fingerprint correlation.
- Resource blocking: block heavy resources first.
