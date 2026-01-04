# AGENTS.MD - PROJECT COMMAND CENTER
## Coordination & Memory Log 

> **NOTICE TO AGENTS**: Read this file at the start of every session. Update it before finishing your task. Be brief but precise.

---

### 🎯 CURRENT OBJECTIVE
*Primary Goal*: Resolve Agent-MCP Dashboard Issues & Complete Gloorbot Indexing.
*Next Milestone*: Verify cross-agent memory sharing between Codex, Claude Code, and Antigravity.

---

### 🤖 ACTIVE FLEET STATUS
| Agent | Current Task | Status |
| :--- | :--- | :--- |
| **Antigravity (Native)** | Fleet Coordination & Handshake | **Verified & Ready** |
| **Codex** | Waiting for Handshake | Idle |
| **Claude Code** | Waiting for Handshake | Idle |

---

### 📝 RECENT MILESTONES (LAST 24 HOURS)
- **Archive [2026-01-03]**: Unified MCP configs for all agents, established `AGENT_PROTOCOL.md`, and optimized dynamic project detection.
- [2026-01-04]: Found coordinator 500s on `/api/v1/deals/bulk` (UNIQUE constraint) blocking forwarding; added in-batch de-dupe + 409 on integrity errors.
- [2026-01-04]: Security: refused to exfiltrate handshake secret; rotate if exposed.
- [2026-01-04]: Agent-MCP: verified stdio MCP handshake; stdio is newline-delimited JSON; use `--project-dir` to avoid DB locks.
- [2026-01-04]: Coordinator: SQLite upsert for `/api/v1/deals/bulk` + `batch_id` tracing + debug tables (`ingest_events`, `deal_sources`) with ~3-day retention + debug endpoints.
- [2026-01-04]: CheapSkater: ingest now honors `CHEAPSKATER_DB_PATH` (fixes “200 OK but not in UI” DB mismatch) + structured ingest logs + richer `/api/ingest/health`.

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
