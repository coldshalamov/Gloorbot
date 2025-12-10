# Apify Actor Context for Lowe's Scraper

Purpose: give Claude all the signal it needs to port the Lowe's Playwright scraper into an Apify Actor that can crawl all categories/stores without tripping Akamai.

## Build on these
- `app/retailers/lowes.py`: product grid pagination, store context, block/crash detection, pickup filter enforcement, SKU parsing.
- `app/selectors.py`: central selectors for product cards, pagination, store selection.
- `app/extractors/dom_utils.py`: human_wait, pagination helpers, price parsing.
- `app/playwright_env.py` + `app/anti_blocking.py`: headful default, persistent/rotating profiles, stealth hook, proxy/slowmo/wait tuning, mobile device pool, per-store profile cloning, nav semaphore.
- `app/multi_store.py`: URL filtering (blocklist), pacing/jitter, dedupe.
- Catalog inputs: `LowesMap.txt`, `catalog/legacy_building_materials.lowes.yml`, `catalog/building_materials.lowes.yml`, `catalog/wa_or_stores.yml`.
- Fix notes: `CRITICAL_FIXES_20251204.md` (Akamai block/crash/pickup fixes), `LOWES_URL_DISCOVERY_GUIDE.md` (discovery constraints).

## Must-keep behaviors
- Headed Chromium; reuse/rotate user data dirs to keep cookies/consent as needed.
- Apply stealth; allow overriding UA/lang/platform via env; add proxy support.
- Fingerprint/device rotation: mobile/desktop personas, locale/timezone/color-scheme variance.
- Pacing: human_wait with global multipliers; category/zip delay bounds; optional slow-mo; mouse jitter.
- Pickup filter: click on every page of pagination (not just first page).
- Block/crash detection: detect Access Denied/Akamai markers and "Aw, Snap"/OOM; reload/backoff and retry.
- Pagination: use next-button selectors or offset param logic; fall back to scroll if needed.
- URL filtering: use blocklist in `multi_store.py`; dedupe preserving order.

## Actor shape (suggested)
- Input schema: category URLs, stores/zips or store IDs, concurrency, proxy, headless toggle, device pool, wait multiplier, slow-mo ms, userDataDir.
- Browser init: use Playwright launch args from `playwright_env.py`; headed by default; apply stealth and fingerprint rotation (see third_party snippets); use Apify proxy configuration.
- Per-store crawl: set store context (see `set_store_context` in `lowes.py`), then iterate category URLs with pickup filters and pagination; cap simultaneous navigations via semaphore.
- Output: push to Apify Dataset `{store_id, store_name, zip, sku, title, category, product_url, image_url, price, price_was, pct_off, availability, clearance, timestamp}`.
- Retries: exponential backoff around category navigation; on block/crash, back off and reuse/rotate profile; optionally rotate proxy/session.

## Minimal dependencies
Use only what is needed: Playwright, playwright-stealth, tenacity, pydantic (for input parsing), httpx or got-scraping/impit (for HTTP endpoints), python-dotenv (optional). Drop heavy PDF/Excel/Tesseract deps.

## Discovery note
Automated discovery is heavily blocked; rely on provided category lists or manual capture. Actor input should accept user-supplied URLs.
