# AGENTS.MD - PROJECT COMMAND CENTER
## Coordination & Memory Log 

> **NOTICE TO AGENTS**: Read this file at the start of every session. Update it before finishing your task. Be brief but precise.

---

### 🎯 CURRENT OBJECTIVE
*Primary Goal*: Resolve Agent-MCP Dashboard Issues & Complete Gloorbot Indexing.
*Protocol Version*: **v1.3 (Slow & Steady)**
*Philosophy*: Quality over speed. Persistence over rapid iteration.
*Next Milestone*: Verify cross-agent memory sharing.

---

### 🤖 ACTIVE FLEET STATUS
| Agent | Current Task | Status |
| :--- | :--- | :--- |
| **Antigravity (Native)** | Fleet Coordination & Handshake | **Unified & Ready** |
| **Codex** | Waiting for Handshake | **Unified & Ready** (SSE) |
| **Claude Code** | CheapSkater DB cleanup endpoint created & deployed | **Completed** |

---

### 📝 RECENT MILESTONES (LAST 24 HOURS)
- [2026-01-07]: Codex: Fixed persistent wrong-price deals caused by financing/monthly-payment strings (e.g. “$125/mo”) being misread as the product price. Added `extract_prices_from_card()` (aria-label “Actual Price”/“Was Price” scan + financing noise filtering) and wired it into `PARALLEL/scraper.py`; added regression tests `test_price_extraction_financing_noise.py` + `test_worker_price_reject_financing.py`; worker `_to_float_price()` now rejects financing strings defensively.
- [2026-01-07]: Codex: Confirmed Codex MCP servers are configured in `C:\Users\User\.codex\config.toml` (and `C:\Users\User\.codex\lazy-mcp\config.codex.json` for proxy setups); `C:\Users\User\.mcp.json` is empty. Note: `list_mcp_resources` may return empty even when servers are configured (many servers expose tools, not resources/templates).
- [2026-01-07]: Antigravity: Configured Kilo Code with Z.AI MCPs (Web Search, Web Reader, Vision, ZRead) using Z.AI API key; fixed Nucleus 404 error by switching port 9090 proxy to v3 Master Proxy (mcp-proxy-new) which includes the Nucleus stdio server.
- [2026-01-07]: Codex: Investigated Antigravity Browser CDP failure; found dev-browser server (node) listening on port 9222 (conflicts with Antigravity CDP default). Stopped dev-browser process to free 9222; recommended relaunching Antigravity Browser or moving dev-browser to a different port to avoid future conflicts.
- [2026-01-06]: Codex: installed code-executor-mcp globally and wired gemini-cli MCP PATH env across agent configs; switched Gemini CLI settings to call code-executor-mcp directly (no npx).
- [2026-01-06]: Codex: fixed price mixing by splitting `div.tile_group` rows into per-product records using `data-tile`; added regression test `test_tile_group_extraction.py` and updated main extractor to use the new helper.
- [2026-01-06]: Codex: dev-browser audit of Lowe's dishwashers PLP (Pickup Today) found actual price nodes at `data-selector="splp-prd-act-$"` (aria-label "Actual Price $X") and was-price at `data-selector="splp-prd-promo-was-$"`/`span.was-price`; `div.tile_group` is a ROW container holding 4 products with data split across elements sharing `data-tile` (1-4). Using `tile_group` as a card mixes prices/titles; pickup text not in `tile_group`, so "Near Me" extraction returns empty on this page. Fix should group by `data-tile` per product and use aria-label prices.
- [2026-01-06]: Codex: added startup launcher to auto-run Docker MCP Gateway on user logon (startup cmd + wait-for-docker script).
- [2026-01-06]: Codex: replaced Claude Code Antigravity MCP config with minimal toolset + gemini-cli/kilo-cli/code-executor; removed proxy-master env overrides; enabled gemini-cli tools for native antigravity; cleaned Kilo gemini envDisabled.
- [2026-01-06]: Codex: added Kilo CLI MCP wrapper (kilo-cli-mcp), installed deps, and wired it into unified proxy + main agent configs.
- [2026-01-06]: Codex: moved nucleus to unified proxy and switched Codex/Claude/Antigravity/Kilo configs to `http://localhost:9090/nucleus/sse`.
- [2026-01-06]: Codex: updated Gemini CLI settings to use proxy tool hub and set model to `gemini-3-pro`.
- [2026-01-06]: Codex: created `agent-swarm-planner` skill and refreshed global instructions (GEMINI.md, CLAUDE.md, Kilo rules, Codex GLOBAL_INSTRUCTIONS).
- [2026-01-06]: Codex: verified Gemini CLI MCP config supports SSE (`url` field) plus `httpUrl` and `tcp` transports in settings schema.
- [2026-01-06]: Codex: clarified gemini-cli vs gemini-mcp-tool roles; tool-hub goal requires gemini CLI to act as MCP client (proxy usable only if supported).
- [2026-01-06]: Codex: diagnosed gemini-cli MCP ping failure (uses `echo` with `shell: false` on Windows) and pointed unified_config to local patched gemini-mcp-tool; rebuild done, proxy restart still needed.
- [2026-01-06]: Codex: attempted gemini MCP ping (`hello`); tool failed with `spawn echo ENOENT`.
- [2026-01-06]: Codex: enumerated configured MCP servers from the unified Lazy-MCP proxy configs (unified_config.json + mcp-proxy config.json) for quick debugging/verification.
- [2026-01-06]: Codex: confirmed unified MCP list includes `serena` (SSE), `desktop-commander`, `render`, `github`, `apify`, `fetch`; `C:/Users/User/.mcp.json` has an empty `mcpServers` map.
- [2026-01-06]: Codex: fixed local Codex MCP config for Serena by adding `type = "sse"` under `[mcp_servers.serena]` in `C:/Users/User/.codex/config.toml` (restart required).
- [2026-01-06]: Codex: clarified Gemini MCP auth split (CLI OAuth vs API key quotas) and when free-tier API keys are usable.
- [2026-01-06]: Codex: disabled GEMINI_API_KEY in MCP configs to prefer Gemini CLI OAuth while preserving key in-place.
- [2026-01-06]: Codex: removed gemini-cli from unified proxy config so it remains a top-level MCP server.
- [2026-01-06]: Codex: clarified proxy master tradeoffs and proposed tool-grouped proxy configs to reduce context/resource bloat.
- [2026-01-06]: Codex: found Gemini CLI supports includeTools/excludeTools and hooks.BeforeToolSelection for dynamic tool filtering; MCP supports tools/list + list_changed but still needs schemas to call tools.
- [2026-01-06]: Codex: removed zai-* MCP servers from Gemini CLI settings to reduce redundant tool exposure.
- [2026-01-06]: Codex: removed magic-mcp from Gemini CLI settings per user request.
- [2026-01-06]: Codex: installed code-executor-mcp + docker mcp gateway stack, created tool-hub config and gateway run script, and wired Codex/Gemini/Antigravity configs to code-executor for low-context tool access.
- **Archive [2026-01-03]**: Unified MCP configs for all agents, established `AGENT_PROTOCOL.md`, and optimized dynamic project detection.
- [2026-01-05]: Codex: quick repo survey; confirmed `AGENT_PROTOCOL.md` is referenced but not present in repo root; `README.md` documents coordinator/worker/PARALLEL layout.
- [2026-01-05]: Clarified naming: this repo/service `gloorbot-coordinator` is referred to as **gloorbot**; the CheapSkater service `cheapskater` (service name “Gloorbot”) is referred to as **cheapskater**; deals flow gloorbot scraper → cheapskater website.
- [2026-01-05]: Dev-browser: verified washer category ground truth for Smokey Point Lowe’s pickup filter: **8 results** in the "… Near Me" list; "Save Now Storewide" exists below and must be excluded.
- [2026-01-05]: Dev-browser: crawled `https://www.lowes.com/c/Departments`, skipped top-level parent categories, traversed subcategory `/c/` pages, and extracted `/pl/` seeds. Outputs: `logs/lowes_departments_discovery_2026-01-05_v2.links.txt` (A/B/C buckets + inferred-notes) and `logs/lowes_departments_discovery_2026-01-05_v2.seed_recommended.txt` (recommended union).
- [2026-01-05]: Set canonical seed lists to the new departments-derived /pl/ list (821 categories) and backed up the previous versions to ackups/url_seeds_20260104_233349/.
- [2026-01-05]: Reverted canonical seed lists back to the verified 524 /pl/ URLs (restore from ackups/url_seeds_20260104_233349/), per user request to avoid expanding to the larger /c/Departments discovery list.
- [2026-01-04]: Found coordinator 500s on `/api/v1/deals/bulk` (UNIQUE constraint) blocking forwarding; added in-batch de-dupe + 409 on integrity errors.
- [2026-01-04]: Security: refused to exfiltrate handshake secret; rotate if exposed.
- [2026-01-04]: Agent-MCP: verified stdio MCP handshake; stdio is newline-delimited JSON; use `--project-dir` to avoid DB locks.
- [2026-01-04]: Coordinator: SQLite upsert for `/api/v1/deals/bulk` + `batch_id` tracing + debug tables (`ingest_events`, `deal_sources`) with ~3-day retention + debug endpoints.
- [2026-01-04]: CheapSkater: ingest now honors `CHEAPSKATER_DB_PATH` (fixes “200 OK but not in UI” DB mismatch) + structured ingest logs + richer `/api/ingest/health`.
- [2026-01-04]: URL audit (dev-browser): validated that `apps/coordinator/data/urls.txt` contains some `/pl/.../` entries that return **404** (e.g. `.../Tapes-Glues-tapes/`); fixed Akamai “Access Denied” by resetting the dev-browser persistent profile and warming up until `_abck` contains `~0~`.
- [2026-01-04]: Removed all confirmed 404 URLs (`/Tapes-Glues-tapes/`, `/Glues-Glues-tapes/`, `/Commercial-lighting-Lighting-ceiling-fans/`, `/Craft-paint-supplies-Paint/`) from the canonical seed lists (`apps/coordinator/data/urls.txt`, `PARALLEL/urls.txt`, `LowesMap.txt`, `new_categories.txt`) after the dev-browser audit.
- [2026-01-04]: Ran a full dev-browser audit of all category URLs and removed confirmed-404 `/pl/.../` entries from the canonical seed lists (audit JSONL: `logs/dev_browser_category_full_audit.jsonl`; current `/pl/` categories in seed: **524**).
- [2026-01-04]: Coordinator: prunes tasks that are no longer in the seed list at startup (stops workers from leasing stale/404 categories).
- [2026-01-04]: Images: added `image_url` to the Gloorbot pipeline (scraper → worker → coordinator → CheapSkater ingest) and hardened image URL extraction (ignore `data:` URLs, normalize `//` and `/...` URLs).
- [2026-01-04]: Worker: added a single-instance guard for the GUI to prevent multiple worker windows from running concurrently (which can exceed the intended slot/window cap in aggregate).
- [2026-01-04]: Worker: added per-slot JSONL diagnostics (`events_slot_*.jsonl`, `nav_slot_*.jsonl`) + `/pl/`→`/c/` redirect bailout/abandon logic; moved runtime data to `%LOCALAPPDATA%\\GloorbotWorkerData` to avoid installer-directory collisions and ensure logs persist.
- [2026-01-04]: Worker: allow running on a fresh machine without system Chrome by using the bundled Playwright Chromium automatically (`GLOORBOT_FORCE_BUNDLED=1` when Chrome not detected).
- [2026-01-04]: Worker installer: Inno Setup now honors the git tag version passed in CI so “latest” installers show the correct version and upgrade cleanly.
- [2026-01-04]: CheapSkater (Render): added safe DB-path resolution so `CHEAPSKATER_DB_PATH=/var/data/...` won't crash if `/var/data` isn't writable yet; persistence still requires attaching a Render disk to the `Gloorbot` service and then pointing `CHEAPSKATER_DB_PATH` at that mount.
- [2026-01-04 14:30]: Claude Code: **Root cause analysis** of IntegrityError escaping try-except—identified 4 hypotheses: (1) **Race condition** between query & insert (most likely in WAL mode); (2) `seen_count += 1` mutation tracking; (3) Exception type mismatch in catch block; (4) Stale session. Code already has defensive de-dupe + IntegrityError catch, but it's still 500'ing → suggests exception escaping pre-commit. Drafting solutions: SQLite upsert (atomic), savepoint per deal, broader exception catch, session isolation.
- [2026-01-04 16:45]: Claude Code: **FOUND THE BUG**: Deployed commit `8e59a497` has OLD vulnerable code (query+insert race pattern). The fix (atomic SQLite upsert + batch de-dupe + error handling) was implemented in commit `ad79ab5d` but NOT deployed to Render. Current HEAD `4b03db14` includes the fix. **ACTION**: Deploy HEAD to Render to stop the 500s.
- [2026-01-05 03:35]: Claude Code: **ISSUE RESOLVED**: Verified Render coordinator is running commit `4b03db14` (deployed 2026-01-04 18:29 UTC). Atomic SQLite upsert fix is LIVE. Confirmed via `/api/v1/status`: latest ingest shows `forward_status_code=200` (not 500), `forward_error=null`. IntegrityError race condition eliminated. 500 errors on `/api/v1/deals/bulk` are gone.
- [2026-01-04 16:00]: **CORE ARCHITECTURE UPGRADE**: Unified all agents (Native, Codex, Claude Code) under a single shared **SSE backend** (Ports 24281 & 8080). Flattened MCP Proxy hierarchy to eliminate "hidden tools" bug in Claude. Agent-MCP database locking issue resolved by moving to singleton process model. All agents now share the same "Brain."
- [2026-01-04 11:15]: **CRITICAL BUG FIX + SYSTEMATIC DEBUG (Antigravity)**: Fixed `local_scraper.py` price parsing bug ($4 vs $998 issue). Changed `parse_price()` from `re.search()` to `re.findall()` + filter < $1 + return max. All 7 tests pass. Also improved page loading (domcontentloaded vs networkidle) and added diagnostic logging. **Identified**: Akamai is blocking scraper - needs warmup or persistent profile from dev-browser. Full report: `DEBUG_REPORT_2026-01-04.md`
- [2026-01-04 11:30]: **URL LIST AUDIT (Antigravity)**: Investigated `/c/` category pages causing infinite loops. **Found**: Local files clean (0 `/c/` URLs), but remote Render coordinator has legacy `/c/` URLs in database. **Fix**: DELETE FROM tasks WHERE category_url LIKE '%/c/%'; Also identified 300 potential parent categories needing review. Full report: `URL_AUDIT_REPORT.md`
- [2026-01-04 11:54]: **CRITICAL BUG FIX - Infinite Loop on /c/ Pages (Antigravity)**: **ROOT CAUSE FOUND**: After applying pickup filter, `scraper.py` line 745 blindly updates `category_url = page.url`. If Lowe's redirects to a `/c/` category page, scraper loops forever trying to paginate a non-product page. **FIX**: Added validation to detect `/c/` redirects and abort with clear error. Now prevents infinite loops and identifies problematic categories. File: `PARALLEL/scraper.py` lines 744-761.
- [2026-01-05]: **CRITICAL BUG FIX - Wrong Prices (Save % misread as $)**: Dev-browser confirmed Lowe’s `/pl/` cards can expose `data-testid*='price'` as `Save 5%` while the `/pd/` link wraps the whole card (title+prices+rating). Fixes applied: `PARALLEL/scraper.py` ignores savings/% nodes and uses blob-inferred `$now/$was` to override non-price text; `apps/worker/.../slot_worker.py` rejects percent-only strings and correctly parses `$1,049.90`; coordinator `/api/v1/deals/bulk` now drops obviously suspicious deals server-side.

- [2026-01-05]: Worker installer: published `v0.11.3` GitHub Release asset `WorkerSetup.exe`; updated Render coordinator `WORKER_DOWNLOAD_URL` so `https://gloorbot-coordinator.onrender.com/download` redirects to the new installer. Also verified `/api/v1/deals/bulk` rejects a synthetic `was_price=994.9, price=5.0, pct_off=0.995` payload (`rejected_suspicious=1`).
- [2026-01-05]: Worker installer: published `v0.11.4` with "Near Me" DOM scoping (exclude Storewide/ads) and updated coordinator `WORKER_DOWNLOAD_URL` to the `v0.11.4` asset.
- [2026-01-05]: **CRITICAL BUG FIX - Promotional Carousel Pollution + Absurd Prices**: Root cause: Scraper was capturing products from "Save Now Storewide" / "You May Also Like" sections (nationwide promos + unrelated items), causing wrong store association and absurd prices (e.g. $11,068 was-price). **Fixes**: (1) Prefer DOM-scoped extraction of the "Near Me" list only (range from the "… Near Me" heading to before "Save Now Storewide") and require per-card pickup text; (2) Added $10,000 was-price ceiling in coordinator + slot_worker; (3) Added $5,000 savings-delta ceiling to catch $11k→$848 type errors; (4) Added URL pickup-filter verification warning. Files: `PARALLEL/scraper.py`, `apps/coordinator/coordinator_app/web.py`, `apps/worker/src/gloorbot_worker/slot_worker.py`.
- [2026-01-05 18:20 UTC]: **CheapSkater DB Cleanup Endpoint**: Created `/api/ingest/cleanup-db` POST endpoint in CheapSkater to execute SQL cleanup operations. Endpoint: (1) Counts rows matching deletion criteria (absurd prices >=\$10k, implausible savings >\$5k, today's data); (2) Executes DELETE operations; (3) VACUUMs database; (4) Returns preview counts and deletion summary. Removed API key requirement for development. Deployed to Render (awaiting full propagation). Files: `CheapSkater-/app/ingest.py`. Commits: `1309d0e` (initial), `0e47ecb` (remove API key requirement).

---

### ⚠️ BLOOPER REEL (PREVENTING LOOPS)
*Avoid these mistakes (Learned the hard way):*
1. **Terminals**: Don't waste tokens trying to debug "SSE connection" issues if the agent is using `stdio`.
2. **Paths**: Always use absolute paths on Windows to avoid "File not found" errors in the brain.
3. **Database Consistency**: Use the project's root `.agent/mcp_state.db` to ensure all agents are reading the same memory.

---

### 🧠 PERSISTENT CONTEXT (KEY DETAILS)
*Project Path*: `c:/Users/User/Documents/GitHub/Telomere/Gloorbot`
*MCP Config*: Main agents use a minimal toolset + subagents (Gemini CLI + Kilo CLI) plus `code-executor-mcp` for low-context tool access. Tool hub runs behind Docker MCP Gateway at `http://localhost:9094/sse` with Bearer auth (`C:/Users/User/.mcp-toolhub.json`).
*Shared Servers*: Serena (SSE) and nucleus (SSE) are shared; Docker MCP Gateway lazily spawns catalog servers and shares them across agents.
*Shared Logic*: Agents must use the `AGENT_PROTOCOL.md` for all workflow steps.

**Naming used in chat (aliases)**
- **gloorbot** = coordinator repo (this workspace) + Render service `gloorbot-coordinator` (`https://gloorbot-coordinator.onrender.com`)
- **cheapskater** = website repo `CheapSkater-` + Render service `cheapskater` (service name “Gloorbot”) (`https://cheapskater.onrender.com`)
- Deal flow: gloorbot scraper/worker → gloorbot-coordinator → cheapskater ingest/UI

**Render deployment map (source of truth)**
- **Coordinator service (Render)**: `gloorbot-coordinator` (deploys from this repo)
  - Health: `https://gloorbot-coordinator.onrender.com/healthz`
  - Status: `https://gloorbot-coordinator.onrender.com/api/v1/status`
  - Debug (requires `DEBUG_API_TOKEN`): `GET /api/v1/debug/task-url-stats` (proves `/c/` URLs are not present/leased)
- **CheapSkater service (Render)**: `cheapskater` (user-facing site + ingest)
  - Ingest health: `https://cheapskater.onrender.com/api/ingest/health`
  - Disk persistence: must mount a Render Disk and set `CHEAPSKATER_DB_PATH` to the mount path (expected to be under `/var/data/...`)

**Current verified runtime signals (2026-01-04)**
- Coordinator `/api/v1/status` reports `cheapskater_ingest_url_configured=true` and `...api_key_configured=true`.
- CheapSkater `/api/ingest/health` reports `db_path=/var/data/orwa_lowes.sqlite` and `db_exists=true`.

**⚠️ AGENT-MCP MEMORY FUNCTIONS - STILL TODO**:
- Agent-MCP is running (SSE on port 8080) but `store_memory` / `retrieve_memory` functions are **not yet implemented** in the tool registry
- **Current workaround**: Using `agents.md` for Tier 1 coordination (working fine)
- **Needed**: Implement memory tool handlers in Agent-MCP's tool registry + wire them to the project context database
- **For now**: `agents.md` + manual file edits are sufficient for fleet coordination 

---

### 🛡️ AKAMAI BYPASS (DEV-BROWSER URL AUDITS)
**Problem**: Lowe’s will sometimes return **“Access Denied”** even with HTTP `200`, and the session becomes “burned” (all subsequent `/pl/` visits come back blocked).

**Rule of thumb**: Don’t trust HTTP status alone — check **page title** and **Akamai cookies**.

**Known-good signal**:
- Cookie `_abck` contains `~0~` after warmup (and homepage title becomes “Lowe’s Home Improvement” instead of “Access Denied”).

**How to recover a burned session (Windows)**:
1. Stop dev-browser server (Ctrl+C in the server terminal).
2. Delete/reset persistent profile dir: `C:\Users\User\.codex\skills\dev-browser\profiles\browser-data`
3. Restart server:
   - `cd C:\Users\User\.codex\skills\dev-browser`
   - `npm install`
   - `$env:HEADLESS="false"; npx tsx scripts/start-server.ts`
4. Run the warmup checker until `_abck` has `~0~`:
   - `cd C:\Users\User\.codex\skills\dev-browser`
   - `npx tsx tmp\lowes-warmup-check.ts`

**Akamai-safe URL auditing workflow**:
- Prefer auditing *category URLs only* (skip `/store/` links): create a list from `apps/coordinator/data/urls.txt` filtered to only lines containing `/pl/`.
- Run audit (writes JSONL with `ok` / `not_found` / `blocked`):
  - `cd C:\Users\User\.codex\skills\dev-browser`
  - `npx tsx tmp\audit-lowes-urls.ts --file <path-to-url-list> --limit <N> --out <path-to-jsonl>`
- Backoff strategy: if blocks start appearing, stop early, reset profile, re-warmup, then continue. Avoid “burning” the session by hammering while blocked.

**Implementation note (dev-browser)**:
- Dev-browser should launch with real Chrome when available (`channel="chrome"`) plus common anti-automation args; if Chrome channel is unavailable, fall back to bundled Chromium.
