# Gemini CLI Tool Access Fix - Complete Solution

## Problem Summary
Gemini CLI was configured with `code-executor-mcp` expecting it to act as a transparent proxy to 20+ heavy tools (github, render, apify, etc.). However, Gemini CLI couldn't "see through" the code-executor to access these tools, causing it to:
- Search the hard drive for tool names instead of using MCPs
- Try to call broken kilo-cli subagent
- Ignore explicit user instructions to use specific MCPs

## Root Cause
**code-executor-mcp is NOT a transparent MCP proxy.** It's designed to execute Python/JavaScript code, not to expose other MCP servers' tools. Gemini CLI had no way to discover or call the tools behind it.

## The Fix

### What Changed
1. **Removed** `code-executor-mcp` from Gemini CLI settings (it wasn't working as intended)
2. **Added** `opaque-hands` lazy-MCP proxy directly to Gemini CLI
3. **Added** direct access to core MCPs: `nucleus`, `serena`, `enhance-prompt`, `google-scholar`

### New Architecture

```
Gemini CLI
├── Direct MCPs (always loaded)
│   ├── nucleus (shared brain/memory)
│   ├── serena (codebase intelligence)
│   ├── enhance-prompt (prompt optimization)
│   └── google-scholar (academic papers)
│
└── opaque-hands (lazy-loaded proxy)
    ├── github (repos, PRs, issues)
    ├── render (deployment management)
    ├── apify (web scraping actors)
    ├── chrome-devtools (browser automation)
    ├── perplexity-ask (AI web search)
    ├── stackoverflow (coding Q&A)
    ├── arxiv (research papers)
    ├── context7 (long-term memory)
    ├── nano-banana (image generation)
    ├── fetch (HTTP requests)
    └── claude-debugs (code debugging)
```

### How It Works Now

**Lazy Loading**: The `opaque-hands` proxy only spawns MCP servers when their tools are actually called. This keeps Gemini CLI's context small while still giving it access to all 20+ tools.

**Tool Discovery**: Gemini CLI can now:
1. See all available tools from opaque-hands in its tool list
2. Call them directly (e.g., `github_create_issue`, `render_list_services`)
3. The proxy handles spawning the underlying MCP server on-demand

## Files Modified

1. **`c:\Users\User\.gemini\settings.json`**
   - Added `opaque-hands` MCP proxy
   - Added direct MCPs (nucleus, serena, enhance-prompt, google-scholar)
   - Removed `code-executor-mcp`

2. **`c:\Users\User\.gemini\INSTRUCTIONS.md`** (NEW)
   - Comprehensive guide for Gemini CLI on tool usage
   - Explains which tools are available and when to use them
   - Warns against using broken kilo-cli

## Testing the Fix

### Test 1: Check Tool Availability
```bash
gemini --list-extensions
```
You should see tools from github, render, apify, etc.

### Test 2: Use a Heavy Tool
Try asking Gemini CLI:
```
"List my GitHub repositories using the github MCP"
```

It should now:
- ✅ Recognize the github MCP
- ✅ Call the appropriate github tool
- ❌ NOT search the hard drive for "github"

### Test 3: Use Render MCP
```
"Get the schema for the render MCP and list my services"
```

It should now:
- ✅ Use the render MCP tools directly
- ❌ NOT search for "render.yaml" files

## Kilo CLI Issue

**Status**: Still broken, but now Gemini CLI is instructed NOT to use it.

The kilo-cli MCP wrapper exists but the underlying `kilo --auto` command fails with auth errors. Until this is fixed:
- Gemini CLI will NOT attempt to call kilo-cli
- If a task requires kilo, Gemini CLI will escalate to the user

## Why Code-Executor Didn't Work

The `code-executor-mcp` is designed for a different use case:
- **Intended use**: Execute Python/JS code snippets in a sandbox
- **NOT intended**: Act as a transparent proxy to other MCP servers
- **Problem**: Even with `MCP_CONFIG_PATH` set, it doesn't expose the underlying tools to the calling agent

## Alternative Approaches Considered

### ❌ Option 1: Keep code-executor, add discovery helpers
- Would require code-executor to implement MCP tool forwarding
- Not supported by current code-executor implementation

### ❌ Option 2: Add all 20+ MCPs directly to Gemini CLI
- Would bloat context with 100+ tools
- Defeats the purpose of lazy loading

### ✅ Option 3: Use lazy-MCP proxy directly (CHOSEN)
- Tools are lazy-loaded (only spawned when needed)
- Gemini CLI can see all available tools
- No context bloat
- Clean separation between "always-on" and "on-demand" tools

## Monitoring & Debugging

### Check if opaque-hands proxy is working
```powershell
# The proxy should be running when Gemini CLI starts
# Check for mcp-proxy.exe process
Get-Process | Where-Object {$_.ProcessName -like "*mcp-proxy*"}
```

### Check Gemini CLI logs
```powershell
# Gemini CLI logs are in:
$env:USERPROFILE\.gemini\logs\
```

### If tools still don't work
1. Verify `opaque_config.json` has the correct paths
2. Check that the underlying MCP servers (github, render, etc.) can start independently
3. Look for errors in Gemini CLI output when calling a tool

## Next Steps

1. **Test the fix**: Try the test cases above
2. **Update global instructions**: If needed, update `INSTRUCTIONS.md` based on real-world usage
3. **Fix kilo-cli** (optional): Resolve the auth issues if you want to use kilo as a subagent
4. **Monitor performance**: Watch for any lazy-loading delays or errors

## Summary

**Before**: Gemini CLI had tools configured but couldn't access them → searched hard drive, tried broken kilo-cli

**After**: Gemini CLI has direct access to all tools via lazy-MCP proxy → can discover and use them properly

The fix is **architectural**, not just configuration. We replaced a non-working proxy pattern (code-executor) with a working one (opaque-hands lazy-MCP).
