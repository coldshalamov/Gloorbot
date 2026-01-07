# Gemini MCP + Kilo MCP handoff (Windows)

This document is a “state of the union” for the two local MCP stdio wrappers we use:

- **`gemini-cli` MCP**: wrapper around the local **Gemini CLI** binary (`gemini`).
- **`kilo-cli` MCP**: wrapper around the local **Kilo Code CLI** binary (often invoked as `kilo`, binary name `kilocode`).

It focuses on: what works, what’s broken, and how to debug quickly.

---

## Where configs live

### Codex (Codex CLI) MCP config

- `C:\Users\User\.codex\config.toml`
- If using Lazy-MCP proxy setups: `C:\Users\User\.codex\lazy-mcp\config.codex.json`

### Claude Code / Antigravity “Claude Code style” MCP config

- `mcp_settings.json` (location depends on your IDE/host; commonly under the user profile / Claude settings)

The relevant servers in both configurations are typically:

- `gemini-cli` → Node stdio server at `index.js`
- `kilo-cli` → Node stdio server at `index.js`

---

## Gemini MCP (`gemini-cli`) — WORKING

### What it is

An MCP stdio wrapper around the local **Gemini CLI**.

- Server entrypoint: `index.js`
- Tool implementations (built output): `dist\tools\*`

### Root cause of previous failures

On Windows, `spawn("gemini", ...)` with `shell: false` often fails because the Gemini CLI is frequently installed as a `gemini.cmd` shim (PATHEXT resolution doesn’t behave like a shell lookup).

Symptoms:

- `spawn gemini ENOENT`
- Or “Transport closed” due to the MCP process crashing early

### Fix applied

Patch in the MCP server’s command executor:

- If `process.platform === "win32"` and command is `gemini`, spawn via **`cmd /c gemini ...`** so `.cmd` shims resolve.

### Quick debug checklist (if it breaks again)

1. Ensure `C:\Users\User\AppData\Roaming\npm` is on `PATH` for the MCP server’s process.
2. Confirm `where gemini` resolves to a `gemini.cmd`.
3. Restart the MCP host (IDE/extension) so the stdio server reloads.
4. Re-test in order:
   - `gemini-cli.ping`
   - `gemini-cli.ask-gemini` (trivial prompt)

---

## Kilo MCP (`kilo-cli`) — MCP OK, underlying Kilo CLI not completing requests

This is a **two-layer** situation:

1. MCP wrapper transport + job management (**working**)
2. Kilo CLI “auto mode” provider/auth/config (**currently failing**)

### Part A: MCP layer (wrapper) — WORKING

#### What it is

An MCP stdio wrapper around **Kilo Code CLI** (`kilo` / `kilocode`).

- Server entrypoint: `index.js`

#### Why it used to time out

The original wrapper ran `kilo --auto ...` synchronously and waited for completion.

Many MCP clients have tool-call deadlines around ~60s, so long jobs would often time out even if Kilo would eventually complete.

#### Fix applied

Converted the wrapper to an **async job model**:

- `kilo_task(...)` starts a background job and returns quickly (`jobId` + stdout/stderr tails).
- Added polling/cancel/list tools:
  - `kilo_task_status({ jobId })`
  - `kilo_task_cancel({ jobId })`
  - `kilo_task_list({ limit })`
- Added `waitSeconds` (default 20, max 25) so short tasks can finish inline without client timeouts.
- Added `--nosplash` to reduce noise.
- Added early-abort detection for “stuck waiting for auth/interactive setup”.

#### Local “is MCP alive?” checks (independent of IDE host)

This repo contains a smoke test that performs a real MCP stdio handshake:

- `tools\kilo_mcp_smoke_test.js`

Expected behavior:

- `initialize` succeeds
- `tools/list` succeeds
- `tools/call` for `kilo_task` returns a `jobId`
- if needed, cancels the job cleanly

### Part B: Kilo CLI itself — NOT WORKING in `--auto` mode (auth/config issue)

#### Observed failure

Jobs start, but Kilo CLI outputs errors such as:

- “Cannot complete request, make sure you are connected and logged in with the selected provider.”
- “KiloCode token + baseUrl is required to fetch models”
- sometimes “ExtensionService not ready”

And/or exits with a timeout-like code (observed: `124`) after waiting.

This indicates **the MCP wrapper is spawning correctly** and capturing output, but Kilo itself is failing before it can answer prompts.

#### Next debugging steps (fix Kilo first, then MCP)

1. Reproduce outside MCP:
   - `kilo --auto --json --mode ask --workspace <repo> --timeout 20 --yolo "hi"`
2. If the same token/baseUrl/provider error appears, MCP isn’t the problem.
3. Fix Kilo auth/provider setup interactively:
   - `kilo auth` (complete provider login/config)
4. Re-test the direct CLI command in step (1) until it returns a real model response.
5. Only then re-test via MCP:
   - call `kilo_task` with `waitSeconds: 2` (or `waitSeconds: 0` to return immediately)
   - poll with `kilo_task_status({ jobId })`

#### Debug artifacts / paths

Common Kilo CLI paths (may vary by version, but typically under this root):

- `C:\Users\User\.kilocode\cli\config.json`
- `C:\Users\User\.kilocode\cli\global-state.json`
- `C:\Users\User\.kilocode\cli\secrets.json`
- `C:\Users\User\.kilocode\cli\workspaces\`

---

## Summary (for next agent)

- **Gemini MCP** was broken due to Windows `.cmd` shim spawning; fixed by running `gemini` through `cmd /c` inside the MCP server. Verified working after restart.
- **Kilo MCP wrapper** was broken due to synchronous long-running tool calls; fixed by async job model with polling tools. MCP layer works.
- **Kilo CLI** is currently failing in `--auto` mode due to provider/auth/baseUrl issues, so jobs time out. Fix Kilo auth/config first; MCP is no longer the blocker.

