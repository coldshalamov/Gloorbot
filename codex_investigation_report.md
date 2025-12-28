# Gloorbot Worker Blocking Investigation Report
Date: 2025-12-28
Scope: PARALLEL (Gloorbot/PARALLEL), Cheapskater, GloorbotWorker (apps/worker)

This report compares stealth usage, browser launch config, build packaging, and
execution flow to identify why GloorbotWorker gets blocked on fresh installs.

## A. Stealth Implementation Comparison

| Aspect | PARALLEL | Cheapskater | GloorbotWorker |
| --- | --- | --- | --- |
| Stealth library used | None; header explicitly says no stealth | playwright_stealth (Stealth) | playwright_stealth (Stealth) |
| How stealth is applied | N/A | apply_stealth -> Stealth.hook_playwright_context(playwright) | Stealth.hook_playwright_context(p) |
| When stealth is applied | N/A | Before launch_browser in main flow | Before launch_persistent_context in ensure_store |
| Per-page stealth_async? | No | No | No |
| File + line | `PARALLEL/scraper.py:8` | `app/playwright_env.py:87`, `app/playwright_env.py:94`, `app/main.py:1037`, `app/main.py:1165` | `apps/worker/src/gloorbot_worker/slot_worker.py:182`, `apps/worker/src/gloorbot_worker/slot_worker.py:188` |

## B. Browser Launch Comparison

| Aspect | PARALLEL | Cheapskater | GloorbotWorker |
| --- | --- | --- | --- |
| Browser type | Playwright Chromium w/ channel "chrome" (system Chrome) | Playwright Chromium (channel default "chromium") | Playwright Chromium (no channel) |
| channel parameter | "chrome" | env CHEAPSKATER_BROWSER_CHANNEL default "chromium" | not set |
| headless | False | env CHEAPSKATER_HEADLESS default False | False |
| args list (full) | --disable-blink-features=AutomationControlled; --disable-dev-shm-usage; --disable-infobars; --disable-gpu; --no-sandbox; --disable-background-networking; --disable-background-timer-throttling; --disable-backgrounding-occluded-windows; --disable-renderer-backgrounding; --memory-pressure-off | --disable-blink-features=AutomationControlled; --disable-dev-shm-usage; --disable-features=IsolateOrigins,site-per-process; --disable-infobars; --lang=en-US; --no-default-browser-check; --start-maximized; --window-size=1440,960; plus CHEAPSKATER_CHROMIUM_ARGS | --disable-blink-features=AutomationControlled; --disable-dev-shm-usage; --disable-features=IsolateOrigins,site-per-process; --disable-infobars; --lang=en-US; --no-default-browser-check; --start-maximized; --window-size=1440,960 |
| slow_mo | none | optional env CHEAPSKATER_SLOW_MO_MS | 12 ms |
| viewport | 1440x900 (launch kwargs) | 1440x900 (context) | 1440x900 (launch kwargs) |
| locale / timezone | en-US / America/Los_Angeles | not set in launch or context | en-US / America/Los_Angeles |
| user_agent | not set | optional USER_AGENT env used in context | not set |
| profile path | .playwright-profiles/store-<id> | .playwright-profile/chromium (persistent) | %LOCALAPPDATA%\GloorbotWorker\profiles\store-<id> |
| File + line | `PARALLEL/scraper.py:760`, `PARALLEL/scraper.py:762`, `PARALLEL/scraper.py:766`, `PARALLEL/scraper.py:783` | `app/playwright_env.py:131`, `app/playwright_env.py:153`, `app/playwright_env.py:171`, `app/retailers/lowes.py:1156`, `app/retailers/lowes.py:1160`, `app/playwright_env.py:100` | `apps/worker/src/gloorbot_worker/slot_worker.py:162`, `apps/worker/src/gloorbot_worker/slot_worker.py:174`, `apps/worker/src/gloorbot_worker/slot_worker.py:197`, `apps/worker/src/gloorbot_worker/paths.py:7` |

## C. PyInstaller Build Analysis

- PLAYWRIGHT_BROWSERS_PATH in build: set to `$PWD/apps/worker/ms-playwright` before install (`.github/workflows/worker-build.yml:37`, `.github/workflows/worker-build.yml:38`).
- Browser install location: `apps/worker/ms-playwright` during build (`.github/workflows/worker-build.yml:39`), bundled via `--add-data "ms-playwright;ms-playwright"` (`.github/workflows/worker-build.yml:49`).
- Runtime browser path: slot worker sets PLAYWRIGHT_BROWSERS_PATH to `<exe_dir>\\ms-playwright` if not already set (`apps/worker/src/gloorbot_worker/slot_worker.py:113`, `apps/worker/src/gloorbot_worker/slot_worker.py:119`).
- Installer packaging: Inno Setup includes entire dist folder, so ms-playwright is expected to ship with the exe (`apps/worker/installer/worker.iss:21`).
- playwright_stealth assets: PyInstaller is configured with `--collect-all "playwright_stealth"` (`.github/workflows/worker-build.yml:56`), so JS assets should be bundled; if this fails, slot_worker logs a stealth hook failure (`apps/worker/src/gloorbot_worker/slot_worker.py:192`).
- Note vs. recommended pattern: the build does not set PLAYWRIGHT_BROWSERS_PATH=0; it uses a custom path instead (`.github/workflows/worker-build.yml:37`, `.github/workflows/worker-build.yml:38`).

## D. Execution Flow Differences (startup -> first page load)

PARALLEL:
- Orchestrator launches worker.py subprocess per store (`PARALLEL/orchestrator.py:130`, `PARALLEL/orchestrator.py:146`).
- worker.py runs scraper.main (`PARALLEL/worker.py:1`).
- scraper opens Playwright, launches persistent context using Chrome channel, creates page (`PARALLEL/scraper.py:750`, `PARALLEL/scraper.py:762`, `PARALLEL/scraper.py:783`, `PARALLEL/scraper.py:784`).
- warmup_session navigates to https://www.lowes.com/ with human behavior (`PARALLEL/scraper.py:124`, `PARALLEL/scraper.py:134`).
- set_store_context navigates to store URL (`PARALLEL/scraper.py:148`, `PARALLEL/scraper.py:152`).
- Delay between categories is 2.0-4.55s (`PARALLEL/scraper.py:802`).

Cheapskater:
- app/main.py -> _run_cycle -> apply_stealth -> launch_browser (`app/main.py:1165`, `app/playwright_env.py:171`).
- launch_browser uses persistent profile and Chromium channel (`app/playwright_env.py:153`, `app/playwright_env.py:177`).
- run_for_zip creates context/page and jitters mouse (`app/retailers/lowes.py:1172`, `app/retailers/lowes.py:1175`, `app/retailers/lowes.py:1203`).
- set_store_context goes to https://www.lowes.com/ (`app/retailers/lowes.py:443`).
- category scraping uses page.goto on category URLs (`app/retailers/lowes.py:694`) with category pause (`app/retailers/lowes.py:142`, `app/retailers/lowes.py:1267`, `app/playwright_env.py:215`).

GloorbotWorker:
- gloorbot_worker/__main__.py dispatches to slot_worker in slot mode (`apps/worker/src/gloorbot_worker/__main__.py:20`).
- slot_worker sets PLAYWRIGHT_BROWSERS_PATH and starts Playwright (`apps/worker/src/gloorbot_worker/slot_worker.py:113`, `apps/worker/src/gloorbot_worker/slot_worker.py:138`).
- ensure_store applies stealth hook, launches persistent Chromium context, creates page (`apps/worker/src/gloorbot_worker/slot_worker.py:182`, `apps/worker/src/gloorbot_worker/slot_worker.py:197`, `apps/worker/src/gloorbot_worker/slot_worker.py:202`).
- warmup_session and set_store_context come from PARALLEL (`apps/worker/src/gloorbot_worker/slot_worker.py:212`, `apps/worker/src/gloorbot_worker/slot_worker.py:213`, `PARALLEL/scraper.py:124`, `PARALLEL/scraper.py:148`).
- Inter-lease delay is 2.0-2.55s (`apps/worker/src/gloorbot_worker/slot_worker.py:308`).

## E. Root Cause Determination (ranked)

[Most likely] Stealth is applied with the wrong Python API in GloorbotWorker, so navigator.webdriver remains true.
- Evidence: GloorbotWorker uses `Stealth.hook_playwright_context(p)` (apps/worker/src/gloorbot_worker/slot_worker.py:182, apps/worker/src/gloorbot_worker/slot_worker.py:188). The provided finding says Python requires `await stealth_async(page)` before navigation. No per-page stealth_async usage exists in GloorbotWorker or Cheapskater.
- Evidence: Akamai detection relies on navigator.webdriver (Finding 3). GloorbotWorker uses Playwright Chromium (apps/worker/src/gloorbot_worker/slot_worker.py:195) which exposes webdriver=true unless patched.
- Evidence: PARALLEL explicitly avoids stealth and uses real Chrome channel (PARALLEL/scraper.py:8, PARALLEL/scraper.py:762), which is the most consistent fingerprint and does not get blocked.

[Second likely] Browser choice mismatch: PARALLEL uses system Chrome while GloorbotWorker uses bundled Chromium.
- Evidence: PARALLEL uses channel "chrome" (PARALLEL/scraper.py:762) and works; GloorbotWorker launches Playwright Chromium without channel (apps/worker/src/gloorbot_worker/slot_worker.py:197). Chromium + new profile is more likely to be flagged than real Chrome.
- Cheapskater also uses Chromium but is paced differently (zip-based flow, preflight, its own human_wait), so it may evade blocks despite Chromium.

[Third likely] Packaging or runtime stealth asset/binary mismatch causes stealth to no-op on fresh installs.
- Evidence: Build uses a custom PLAYWRIGHT_BROWSERS_PATH instead of "0" (worker-build.yml:37, worker-build.yml:38), relies on ms-playwright being present next to the exe (apps/worker/src/gloorbot_worker/slot_worker.py:113), and only best-effort stealth hooking (apps/worker/src/gloorbot_worker/slot_worker.py:192).
- If the ms-playwright folder or playwright_stealth assets are missing/corrupt, the worker will silently fall back to unpatched Chromium and be blocked.

## F. Proposed Fix (for most likely cause)

Exact file to modify:
- `apps/worker/src/gloorbot_worker/slot_worker.py`

Exact change:
- Remove the context-level stealth hook at `apps/worker/src/gloorbot_worker/slot_worker.py:182` / `apps/worker/src/gloorbot_worker/slot_worker.py:188`.
- Apply per-page stealth immediately after page creation at `apps/worker/src/gloorbot_worker/slot_worker.py:202`, before any navigation (warmup/session).

Proposed code (insert after page creation):
```python
from playwright_stealth import stealth_async

# after: page = context.pages[0] if context.pages else await context.new_page()
try:
    await stealth_async(page)
    print(f"[slot-{slot_id}] Stealth mode enabled", flush=True)
except ImportError:
    print(f"[slot-{slot_id}] playwright_stealth not installed, using basic mode", flush=True)
except Exception as e:
    print(f"[slot-{slot_id}] Stealth hook failed (non-fatal): {e}", flush=True)
```

How to verify the fix works:
1) Fresh profile test: delete `%LOCALAPPDATA%\GloorbotWorker\profiles` and run a single slot. Confirm no "Access Denied"/"Robot" page during warmup.
2) Add a one-time diagnostic in dev mode: `print(await page.evaluate("navigator.webdriver"))` after `stealth_async(page)`; it should be False/undefined before the first `page.goto`.
3) Compare against PARALLEL timing: ensure warmup and set_store_context still run unchanged (`PARALLEL/scraper.py:124`, `PARALLEL/scraper.py:148`).

Optional hardening (if blocking persists):
- Switch to real Chrome channel or CDP connection (Finding 4). This aligns GloorbotWorker with PARALLEL's known-good fingerprint (`PARALLEL/scraper.py:762`).
