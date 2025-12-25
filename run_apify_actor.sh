#!/bin/bash
# Apify Actor Runner Script
# Usage: ./run_apify_actor.sh <actor_name> <input_json_file>

APIFY_TOKEN="apify_api_3IKAywfQMTkpNC0xtNpQo0IwjYc6e312N9dM"
ACTOR_NAME="${1:-lowes-cheapskate}"
INPUT_FILE="${2:-input.json}"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Creating default input.json..."
    cat > input.json <<'EOF'
{
  "stores": [{"store_id": "0004", "name": "Test Store", "zip": "98144"}],
  "categories": [{"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"}],
  "max_pages_per_category": 2
}
EOF
    INPUT_FILE="input.json"
fi

echo "Running actor: one-api/$ACTOR_NAME"
echo "Input: $INPUT_FILE"
echo ""

RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d @"$INPUT_FILE" \
  "https://api.apify.com/v2/acts/one-api~$ACTOR_NAME/runs")

RUN_ID=$(echo "$RESPONSE" | jq -r '.data.id')

if [ "$RUN_ID" = "null" ] || [ -z "$RUN_ID" ]; then
    echo "Error starting actor:"
    echo "$RESPONSE" | jq '.'
    exit 1
fi

echo "✓ Actor started successfully!"
echo "Run ID: $RUN_ID"
echo ""
echo "Monitoring status..."

while true; do
    STATUS_RESPONSE=$(curl -s -H "Authorization: Bearer $APIFY_TOKEN" \
        "https://api.apify.com/v2/actor-runs/$RUN_ID")

    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.data.status')

    echo "[$(date +%H:%M:%S)] Status: $STATUS"

    if [ "$STATUS" = "SUCCEEDED" ]; then
        echo ""
        echo "✓ Actor completed successfully!"

        DATASET_ID=$(echo "$STATUS_RESPONSE" | jq -r '.data.defaultDatasetId')
        echo "Dataset ID: $DATASET_ID"
        echo ""
        echo "Downloading results..."

        curl -s -H "Authorization: Bearer $APIFY_TOKEN" \
            "https://api.apify.com/v2/datasets/$DATASET_ID/items?format=json" > "results_${RUN_ID}.json"

        ITEM_COUNT=$(jq '. | length' "results_${RUN_ID}.json")
        echo "✓ Downloaded $ITEM_COUNT items to results_${RUN_ID}.json"
        break
    elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "ABORTED" ] || [ "$STATUS" = "TIMED-OUT" ]; then
        echo ""
        echo "✗ Actor failed with status: $STATUS"
        echo ""
        echo "Error details:"
        echo "$STATUS_RESPONSE" | jq '.data'
        exit 1
    fi

    sleep 10
done
