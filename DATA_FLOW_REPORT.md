# Gloorbot → CheapSkater Data Flow Report

**Date**: 2026-01-03
**Status**: ⚠️ **MISCONFIGURED - Data is NOT flowing to CheapSkater**

## Executive Summary

The Gloorbot Coordinator is running on Render and receiving/storing deals correctly. However, **the data is NOT being forwarded to CheapSkater** because critical environment variables are missing on the Coordinator service.

## Current System Status

### ✅ Working Components

1. **Gloorbot Coordinator** (https://gloorbot-coordinator.onrender.com)
   - Service is healthy and responsive
   - Health endpoint returns `{'ok': True}`
   - Database is receiving and storing deals

2. **CheapSkater Dashboard** Service exists
   - Available on Render but ingest endpoint returning 404
   - Indicates ingest.py router may not be registered

### ❌ Broken Components

1. **Coordinator → CheapSkater Integration**
   - **Missing**: `CHEAPSKATER_INGEST_URL` environment variable
   - **Missing**: `CHEAPSKATER_INGEST_API_KEY` environment variable
   - Without these, the coordinator cannot forward deals to CheapSkater

2. **CheapSkater Ingest Endpoint**
   - Returning HTTP 404 on `/api/ingest/health`
   - This suggests the ingest router is NOT registered in the FastAPI app
   - The code for ingest.py exists (see `app/ingest.py`) but may not be wired up

## The Data Flow Architecture

```
Your Local Scraper
    ↓
    POST /api/v1/client/register
    POST /api/v1/deals/bulk
    ↓
Gloorbot Coordinator (Render)
    ├→ Stores deals in its database ✅
    └→ Forwards to CheapSkater ❌ (BROKEN - no env vars)
        ↓
CheapSkater Dashboard (Render)
    ├→ /api/ingest/deals endpoint
    └→ Stores in orwa_lowes.sqlite
```

## What's Happening Right Now

1. **Coordinator Code** (apps/coordinator/web.py, lines 40-41, 56-79, 366-430):
   ```python
   CHEAPSKATER_INGEST_URL = os.getenv("CHEAPSKATER_INGEST_URL", "")
   CHEAPSKATER_INGEST_API_KEY = os.getenv("CHEAPSKATER_INGEST_API_KEY", "")

   def _forward_deals_to_cheapskater(deals: list[dict]) -> None:
       if not CHEAPSKATER_INGEST_URL or not deals:
           return  # ← SILENTLY EXITS if URL not configured
   ```

2. **Current Behavior**:
   - Your local scraper sends deals to Coordinator ✅
   - Coordinator receives and stores them ✅
   - Coordinator checks if `CHEAPSKATER_INGEST_URL` is set ❌
   - Since it's empty, forwarding is SKIPPED (no error, just silent failure)
   - Deals never reach CheapSkater ❌

## What Needs to Be Fixed

### **CRITICAL: Fix Environment Variables on Render**

Go to [https://dashboard.render.com](https://dashboard.render.com) and:

1. **Open the `gloorbot-coordinator` service**
2. **Click Settings → Environment**
3. **Add these variables**:
   - `CHEAPSKATER_INGEST_URL` = `https://cheapskater-dashboard.onrender.com/api/ingest/deals`
   - `CHEAPSKATER_INGEST_API_KEY` = *(generate a secure secret key, e.g., using `openssl rand -base64 32`)*

4. **Save and redeploy** the coordinator service

### **IMPORTANT: Set API Key on CheapSkater**

1. **Open the `cheapskater-dashboard` service** on Render
2. **Click Settings → Environment**
3. **Add/update this variable**:
   - `CHEAPSKATER_INGEST_API_KEY` = *(use the SAME key you set on Coordinator)*

4. **Save and redeploy** the CheapSkater service

### **VERIFY: Check Ingest Router Registration**

The CheapSkater service is returning 404 on the ingest endpoint. Verify that `app/dashboard.py` has:

```python
from app.ingest import router as ingest_router
app.include_router(ingest_router)
```

Lines 51-52 of `CheapSkater-/app/dashboard.py` should have this. If not, add it after the `app = FastAPI(...)` line.

## Verification Checklist

After making changes, verify by:

1. **Check Coordinator logs** on Render dashboard:
   - Look for: `"Forwarded X deals to Cheapskater: accepted=X"`
   - If the URL is set, you should see these messages when deals are sent

2. **Check CheapSkater logs** on Render dashboard:
   - Look for: `"Processed X deals from gloorbot"`
   - Indicates data was successfully ingested

3. **Run the debug script again**:
   ```bash
   python debug_data_flow.py
   ```
   Should show:
   - ✅ Coordinator environment variables are set
   - ✅ CheapSkater ingest endpoint returns 200
   - ✅ Database counts increase in both services

## Code References

- **Coordinator forwarding logic**: [apps/coordinator/coordinator_app/web.py:40-79](apps/coordinator/coordinator_app/web.py#L40-L79)
- **Coordinator deals endpoint**: [apps/coordinator/coordinator_app/web.py:366-430](apps/coordinator/coordinator_app/web.py#L366-L430)
- **CheapSkater ingest endpoint**: [app/ingest.py:127-202](../CheapSkater-/app/ingest.py#L127-L202)
- **CheapSkater router registration**: [app/dashboard.py:50-52](../CheapSkater-/app/dashboard.py#L50-L52)

## Why This Silent Failure Happened

The code is designed to be graceful and not crash if CheapSkater is not available. However, this means:
- No error messages in logs if URL is missing
- No indication that forwarding isn't happening
- Deals pile up in Coordinator but never reach CheapSkater

This is why the debug script was needed to diagnose the issue!

## Next Steps

1. **Set environment variables** on Render (takes ~2-5 minutes per service)
2. **Verify ingest router** registration on CheapSkater
3. **Redeploy both services** (automatic via Render)
4. **Monitor logs** to confirm data is flowing
5. **Run debug script again** to verify everything works

---

**Need help with Render configuration?**
- [Render Environment Variables Documentation](https://render.com/docs/environment-variables)
- Set variables in: Dashboard → Service → Settings → Environment
