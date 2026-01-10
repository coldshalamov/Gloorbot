# Breadcrumb Category Mapping (Akamai-safe)

This project intentionally **does not** change the working scraper/worker to become “breadcrumb aware”.
Instead, we enrich categories **downstream** using a separate breadcrumb-mapping step powered by `dev-browser`
(persistent, warmed session) and store the results in the coordinator DB.

## Why

Some Lowe’s category URLs are not reliably human-decodable (numeric/hyphenated IDs, inconsistent slugs).
Breadcrumbs expose the canonical, hierarchical category names directly in the DOM.

## How It Works

- Use `dev-browser` to visit category URLs and extract breadcrumbs.
- POST the extracted breadcrumbs to the coordinator debug endpoint.
- Coordinator stores `category_meta` and uses it as an override during `/api/v1/deals/bulk` ingest:
  - If a mapping exists for `category_url`, it wins.
  - Otherwise, fall back to URL slug parsing.

## Coordinator Endpoint

- `POST /api/v1/debug/category-meta/bulk`
- Requires header: `x-debug-token: <DEBUG_API_TOKEN>`
- Body:

```json
{
  "items": [
    {
      "category_url": "https://www.lowes.com/pl/air-conditioners-fans/portable-fans/4294856700",
      "breadcrumbs": [
        { "text": "Heating & Cooling", "href": "/c/Heating-cooling" },
        { "text": "Air Conditioners & Fans", "href": "/c/Air-conditioners-fans-Heating-cooling" },
        { "text": "Portable Fans", "href": "/pl/air-conditioners-fans/portable-fans/4294856700" }
      ]
    }
  ]
}
```

## Dev-Browser Workflow (Windows)

Follow the repo’s Akamai warmup guidance (see `AGENTS.md`).

1. Start dev-browser (global skill):
   - `cd C:\Users\User\.codex\skills\dev-browser`
   - `$env:HEADLESS="false"; npx tsx scripts/start-server.ts`

2. Warm the session until it’s “good” (`_abck` contains `~0~`):
   - `cd C:\Users\User\.codex\skills\dev-browser`
   - `npx tsx tmp\lowes-warmup-check.ts`

3. Extract breadcrumbs for a few URLs:
   - `cd C:\Users\User\.codex\skills\dev-browser`
   - `npx tsx tmp\breadcrumb-audit.ts`

4. Upload to coordinator:
   - Use any HTTP client to post the JSON payload to your coordinator instance.
   - For Render, this will be something like:
     - `https://gloorbot-coordinator.onrender.com/api/v1/debug/category-meta/bulk`

## Notes

- This approach avoids touching `PARALLEL/scraper.py` or the worker deal payload format.
- Once `category_meta` has coverage for the seed list, category filtering becomes robust even for “opaque” URLs.

