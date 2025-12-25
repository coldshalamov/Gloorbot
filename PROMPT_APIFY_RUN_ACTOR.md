# Run Apify Actor with Your API Key

## Your Apify Credentials
- **API Key**: `apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM`
- **Username**: `one-api`
- **API Base URL**: `https://api.apify.com/v2`

## Your Available Actors
1. **lowes-cheapskate** - Optimized Lowe's scraper
2. **lowe-s-products-full-optimized** - Full Lowe's product scraper
3. **lowes-products-scraper** - Basic Lowe's scraper
4. **skip-trace** - Skip trace actor

## Direct API Commands (Copy & Paste)

### 1. List All Your Actors
```bash
curl -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
     https://api.apify.com/v2/acts
```

### 2. Run the lowes-cheapskate Actor
```bash
curl -X POST \
  -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
  -H "Content-Type: application/json" \
  -d '{
    "stores": [{"store_id": "0004", "name": "Test Store", "zip": "98144"}],
    "categories": [{"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"}],
    "max_pages_per_category": 2
  }' \
  https://api.apify.com/v2/acts/one-api~lowes-cheapskate/runs
```

### 3. Get Actor Run Status
```bash
# Replace RUN_ID with the actual run ID from step 2
curl -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
     https://api.apify.com/v2/actor-runs/RUN_ID
```

### 4. Get Dataset from Run
```bash
# Replace DATASET_ID with the dataset ID from the run status
curl -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
     https://api.apify.com/v2/datasets/DATASET_ID/items
```

## Using Python

```python
import requests

API_TOKEN = "apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM"
headers = {"Authorization": f"Bearer {API_TOKEN}"}

# Run actor
response = requests.post(
    "https://api.apify.com/v2/acts/one-api~lowes-cheapskate/runs",
    headers=headers,
    json={
        "stores": [{"store_id": "0004", "name": "Test", "zip": "98144"}],
        "categories": [{"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"}],
        "max_pages_per_category": 2
    }
)

run_id = response.json()["data"]["id"]
print(f"Run started: {run_id}")

# Check status
status = requests.get(
    f"https://api.apify.com/v2/actor-runs/{run_id}",
    headers=headers
).json()

print(f"Status: {status['data']['status']}")
```

## Using Apify CLI

### Install CLI
```bash
npm install -g apify-cli
```

### Login with Token
```bash
apify login --token apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM
```

### Run Actor
```bash
apify call one-api/lowes-cheapskate \
  --input '{
    "stores": [{"store_id": "0004", "name": "Test Store", "zip": "98144"}],
    "categories": [{"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"}],
    "max_pages_per_category": 2
  }'
```

## Environment Variable Method

Set the token once:
```bash
export APIFY_TOKEN=apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM
```

Then use without specifying token:
```bash
apify call one-api/lowes-cheapskate --input input.json
```

## Full Example Workflow

```bash
# 1. Run the actor
RUN_ID=$(curl -X POST \
  -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
  -H "Content-Type: application/json" \
  -d '{"stores":[{"store_id":"0004"}],"categories":[{"name":"Clearance","url":"https://www.lowes.com/pl/The-back-aisle/2021454685607"}],"max_pages_per_category":2}' \
  https://api.apify.com/v2/acts/one-api~lowes-cheapskate/runs | jq -r '.data.id')

echo "Run ID: $RUN_ID"

# 2. Wait for completion (check every 10 seconds)
while true; do
  STATUS=$(curl -s -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
    https://api.apify.com/v2/actor-runs/$RUN_ID | jq -r '.data.status')

  echo "Status: $STATUS"

  if [ "$STATUS" = "SUCCEEDED" ] || [ "$STATUS" = "FAILED" ]; then
    break
  fi

  sleep 10
done

# 3. Get the dataset
DATASET_ID=$(curl -s -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
  https://api.apify.com/v2/actor-runs/$RUN_ID | jq -r '.data.defaultDatasetId')

# 4. Download results
curl -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
  "https://api.apify.com/v2/datasets/$DATASET_ID/items?format=json" > results.json

echo "Results saved to results.json"
```

## Quick Test Command

Paste this entire block to test your API key:
```bash
curl -H "Authorization: Bearer apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM" \
     https://api.apify.com/v2/acts | jq '.data.items[] | {name: .name, id: .id}'
```

This should show all your actors without any errors.
