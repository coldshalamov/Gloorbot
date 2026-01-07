# Nucleus Brain (local coordination)

Nucleus is the shared “brain” for this repo on this machine. It stores:
- shared state in `.brain/ledger/state.json`
- shared task queue in `.brain/ledger/tasks.json`
- shared event log in `.brain/ledger/events.jsonl`

All agents should coordinate by **task claiming** (atomic) + emitting events, instead of ad‑hoc notes or file locks.

## Start / stop / status

From repo root:

```powershell
# Status
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nucleus/status-nucleus-brain.ps1

# Start (background)
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nucleus/start-nucleus-brain.ps1

# Stop
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nucleus/stop-nucleus-brain.ps1
```

Default endpoint is `http://127.0.0.1:9090/nucleus/sse`.

## Quick verification

```powershell
curl.exe -i -N http://127.0.0.1:9090/nucleus/sse --max-time 2
```

You should see `HTTP/1.1 200 OK` and `content-type: text/event-stream`.

## Recommended coordination workflow (in your MCP client)

1. Start of session: `brain_get_state` or prompt `cold_start`
2. Before editing: `brain_get_next_task` → `brain_claim_task`
3. Finish: `brain_update_task` (DONE/BLOCKED/ESCALATED) + `brain_emit_event`

