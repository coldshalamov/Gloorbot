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
| **Claude Code** | Investigating IntegrityError race condition in `/api/v1/deals/bulk` | **Unified & Active** (SSE) |

---

### 📝 RECENT MILESTONES (LAST 24 HOURS)
- **Archive [2026-01-03]**: Unified MCP configs for all agents, established `AGENT_PROTOCOL.md`, and optimized dynamic project detection.
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
- [2026-01-04 16:00]: **CORE ARCHITECTURE UPGRADE**: Unified all agents (Native, Codex, Claude Code) under a single shared **SSE backend** (Ports 24281 & 8080). Flattened MCP Proxy hierarchy to eliminate "hidden tools" bug in Claude. Agent-MCP database locking issue resolved by moving to singleton process model. All agents now share the same "Brain."
- [2026-01-04 11:15]: **CRITICAL BUG FIX + SYSTEMATIC DEBUG (Antigravity)**: Fixed `local_scraper.py` price parsing bug ($4 vs $998 issue). Changed `parse_price()` from `re.search()` to `re.findall()` + filter < $1 + return max. All 7 tests pass. Also improved page loading (domcontentloaded vs networkidle) and added diagnostic logging. **Identified**: Akamai is blocking scraper - needs warmup or persistent profile from dev-browser. Full report: `DEBUG_REPORT_2026-01-04.md`
- [2026-01-04 11:30]: **URL LIST AUDIT (Antigravity)**: Investigated `/c/` category pages causing infinite loops. **Found**: Local files clean (0 `/c/` URLs), but remote Render coordinator has legacy `/c/` URLs in database. **Fix**: DELETE FROM tasks WHERE category_url LIKE '%/c/%'; Also identified 300 potential parent categories needing review. Full report: `URL_AUDIT_REPORT.md`
- [2026-01-04 11:54]: **CRITICAL BUG FIX - Infinite Loop on /c/ Pages (Antigravity)**: **ROOT CAUSE FOUND**: After applying pickup filter, `scraper.py` line 745 blindly updates `category_url = page.url`. If Lowe's redirects to a `/c/` category page, scraper loops forever trying to paginate a non-product page. **FIX**: Added validation to detect `/c/` redirects and abort with clear error. Now prevents infinite loops and identifies problematic categories. File: `PARALLEL/scraper.py` lines 744-761.


---

### ⚠️ BLOOPER REEL (PREVENTING LOOPS)
*Avoid these mistakes (Learned the hard way):*
1. **Terminals**: Don't waste tokens trying to debug "SSE connection" issues if the agent is using `stdio`.
2. **Paths**: Always use absolute paths on Windows to avoid "File not found" errors in the brain.
3. **Database Consistency**: Use the project's root `.agent/mcp_state.db` to ensure all agents are reading the same memory.

---

### 🧠 PERSISTENT CONTEXT (KEY DETAILS)
*Project Path*: `c:/Users/User/Documents/GitHub/Telomere/Gloorbot`
*MCP Config*: All agents use the **Unified Lazy-MCP Proxy** pointing to `C:/Users/User/.claude/mcp-servers/lazy-mcp/unified_config.json`.
*Shared Servers*: One instance of Serena and Agent-MCP is shared by all 3 agents via the proxy.
*Shared Logic*: Agents must use the `AGENT_PROTOCOL.md` for all workflow steps.

**✅ MEMORY COORDINATION STACK**:
- **Agent-MCP**: Running (SSE on port 8080) for agent handshake, messaging, task coordination
- **Anthropic Memory Server** (NEW): Added to `unified_config.json` — provides `create_entities`, `add_observations`, `read_graph`, `search_nodes` for persistent fleet memory
- **agents.md**: Tier 1 dashboard (high-level milestones, status table)
- **Lazy-MCP Proxy**: Routes all 3 agents through single proxy — memory tools load on-demand without context bloat 

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
