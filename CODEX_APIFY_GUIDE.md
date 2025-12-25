# How to Use Apify MCP in Codex

## Configuration
The Apify MCP is already configured in your Antigravity IDE with your API token.

**Location**: `C:\Users\User\AppData\Roaming\Antigravity\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

**Your Apify Token**: `apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM`

## Available Actors
You have 4 actors available:
1. **skip-trace** (ID: vmf6h5lxPAkB1W2gT)
2. **lowes-products-scraper**
3. **lowe-s-products-full-optimized**
4. **lowes-cheapskate**

## How to Use Apify MCP in Codex

### Step 1: List Your Actors
Ask Codex:
```
Use the Apify MCP to list all my actors
```

### Step 2: Run an Actor
Ask Codex:
```
Use the Apify MCP to run the lowes-cheapskate actor with this input:
{
  "stores": [{"store_id": "0004", "name": "Test Store"}],
  "categories": [{"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"}],
  "max_pages_per_category": 2
}
```

### Step 3: Get Actor Run Status
Ask Codex:
```
Use the Apify MCP to check the status of actor run <RUN_ID>
```

### Step 4: Get Results
Ask Codex:
```
Use the Apify MCP to get the results from actor run <RUN_ID>
```

## Example Complete Workflow

```
1. "Use Apify MCP to run my lowes-cheapskate actor"
2. Wait for run to complete
3. "Use Apify MCP to get the dataset from that run"
4. "Parse the results and show me the products found"
```

## Troubleshooting

If Codex says it can't access Apify MCP:
1. Restart Antigravity IDE completely
2. Make sure you're using the claude-dev extension (not Cline or other extensions)
3. Check that the MCP servers are loaded by looking at the extension status

## Direct API Alternative

If the MCP still doesn't work, you can ask Codex to use the Apify API directly:

```
Use curl to call the Apify API:
curl -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
     https://api.apify.com/v2/acts/one-api~lowes-cheapskate/runs
```

## Your Apify Account
- **Username**: one-api
- **API Endpoint**: https://api.apify.com/v2
- **Console**: https://console.apify.com

## Environment Variable Method
You can also set the token as an environment variable in Antigravity's terminal:

```bash
export APIFY_TOKEN=apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM
```

Then use the Apify CLI:
```bash
apify actor call one-api/lowes-cheapskate --input '{"stores": [...]}'
```
