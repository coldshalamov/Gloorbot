# Gloorbot -> Cheapskater Integration

This integration pushes deals from the Gloorbot coordinator to the Cheapskater website in real-time.

## Architecture

```
Workers scrape Lowe's
        |
        v
Gloorbot Coordinator (Render)
        |
        +---> Gloorbot deals table
        |
        +---> HTTP POST to Cheapskater
                    |
                    v
           Cheapskater Website (Render)
                    |
                    v
           store_price_history table
                    |
                    v
           cheapskater.onrender.com shows deals!
```

## Setup Instructions

### Step 1: Add the ingest API to Cheapskater

1. Copy `integration/ingest.py` to your Cheapskater repo:
   ```
   copy integration\ingest.py C:\Users\User\Documents\GitHub\Cheapskater_FULL_20251204_132158\app\ingest.py
   ```

2. Edit `app/dashboard.py` in Cheapskater:

   Near the top imports, add:
   ```python
   from app.ingest import router as ingest_router
   ```

   After `app = FastAPI(title="CheapSkater Clearance Dashboard")`, add:
   ```python
   app.include_router(ingest_router)
   ```

3. Commit and push Cheapskater to trigger Render deploy.

### Step 2: Configure Environment Variables on Render

**On Cheapskater service:**
```
CHEAPSKATER_INGEST_API_KEY=gloorbot-secret-key-12345
```

**On Gloorbot Coordinator service:**
```
CHEAPSKATER_INGEST_URL=https://cheapskater.onrender.com/api/ingest/deals
CHEAPSKATER_INGEST_API_KEY=gloorbot-secret-key-12345
```

(Use a real secret key, not the example above)

### Step 3: Deploy Both Services

Push changes to both repos. Render will auto-deploy.

### Step 4: Verify

1. Check Gloorbot coordinator logs for: `Forwarded X deals to Cheapskater`
2. Check Cheapskater at https://cheapskater.onrender.com
3. Deals should appear within seconds of workers finding them

## How It Works

1. **Workers** scrape Lowe's stores for deals (50%+ off)
2. **Workers** POST deals to Gloorbot coordinator at `/api/v1/deals/bulk`
3. **Coordinator** saves to local database AND forwards to Cheapskater
4. **Cheapskater** receives deals at `/api/ingest/deals`
5. **Cheapskater** extracts SKU from URL, category from URL, parses store info
6. **Cheapskater** saves to `store_price_history` table
7. **Website** queries this table and displays deals

## Data Transformation

The integration automatically converts Gloorbot's deal format to Cheapskater's format:

| Gloorbot Field | Cheapskater Field | How |
|----------------|-------------------|-----|
| `product_url` | `sku` | Extract numbers from `/pd/Name/SKU` |
| `category_url` | `category` | Extract name from `/pl/Category/ID` |
| `store_name` | `city`, `state` | Parse "Seattle, WA (#0001)" |
| `price` | `price` | Direct |
| `was_price` | `price_was` | Direct |
| `pct_off` | `pct_off` | Direct |
| (constant) | `retailer` | "lowes" |
| (constant) | `clearance` | true |
| (constant) | `availability` | "In Stock" |

## Files

- `integration/ingest.py` - Copy this to Cheapskater as `app/ingest.py`
- `integration/cheapskater_ingest.py` - Test/reference implementation
- `apps/coordinator/coordinator_app/web.py` - Modified to forward deals

## Testing

Test the conversion logic locally:
```bash
python integration/cheapskater_ingest.py
```

## Troubleshooting

### Deals not appearing on Cheapskater

1. Check Gloorbot coordinator logs for forwarding errors
2. Verify `CHEAPSKATER_INGEST_URL` is correct (include `/api/ingest/deals`)
3. Verify API keys match on both services
4. Check if Cheapskater is running (visit https://cheapskater.onrender.com/api/ingest/health)

### "Invalid API key" error

Make sure `CHEAPSKATER_INGEST_API_KEY` is set identically on both Render services.

### SKU extraction failing

Some Lowe's URLs may not match `/pd/Name/SKU` pattern. Check the `extract_sku_from_url` function.
