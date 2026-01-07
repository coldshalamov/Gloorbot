# Verification Suite

This repo is vulnerable to **silent, long-running regressions** where a rare DOM layout causes:
- `div.tile_group` (multi-product row) to be treated as a single card
- href/title from product A to mix with price/was from product B
- financing/monthly-payment strings to be parsed as real prices

This folder provides a repeatable verification workflow to prevent week-long “it ran for hours then puked a bad deal” failures.

## Tier 1: Deterministic regression suite (recommended, no network)

Run:

```powershell
python verification/run_suite.py
```

What it covers:
- `test_tile_group_extraction.py`: Python locator-path splits `tile_group` by `data-tile`
- `test_near_me_dom_tile_group_split.py`: JS near-me extractor must NOT mix products
- `test_price_extraction_financing_noise.py`: ignores `$125/mo` and similar
- `test_worker_price_reject_financing.py`: worker parsing rejects financing strings

## Tier 2: Optional live Lowe’s smoke test (network + Akamai risk)

This is **optional** because Lowe’s can block automation. It uses a persistent profile at `verification/.pw_profile` so you can warm once and re-run.

Run (PowerShell):

```powershell
$env:GLOORBOT_LIVE_TEST = "1"
$env:GLOORBOT_LIVE_HEADLESS = "0"   # recommended (headful)
python verification/live_smoke_lowes.py
```

Artifacts:
- `verification/.artifacts/*_warmup.png`
- `verification/.artifacts/*_plp.png`
- `verification/.artifacts/*_pdp.png`
- `verification/.artifacts/*_result.json`

Result file includes:
- warmup status (`_abck` ~0~ signal)
- PLP “DOM truth” price nodes
- scraper-extracted price/was
- PASS/FAIL decision

## Using dev-browser skill (manual but reliable)

If the live smoke test is blocked, use the dev-browser scripts (persistent, warmed profile) and compare:
- `C:\Users\User\.codex\skills\dev-browser\tmp\lowes-warmup-check.ts`
- `C:\Users\User\.codex\skills\dev-browser\tmp\check_lowes_product_price.ts`
- `C:\Users\User\.codex\skills\dev-browser\tmp\inspect_lowes_plp_card.ts`

