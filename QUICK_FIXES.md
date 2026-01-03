# Quick Fixes - Gloorbot ↔ CheapSkater Integration

## The Problem in 30 Seconds

✅ Your scraper is sending deals to the Gloorbot Coordinator
✅ The Coordinator is storing deals in its database
❌ **But the Coordinator is NOT forwarding them to CheapSkater because it doesn't know the CheapSkater URL**

## The Fix in 5 Steps

### Step 1: Get the URLs (2 minutes)

Go to https://dashboard.render.com and find these URLs:

1. **For gloorbot-coordinator service**:
   - Copy the URL (should be like `https://gloorbot-coordinator.onrender.com`)

2. **For cheapskater-dashboard service**:
   - Copy the URL (should be like `https://cheapskater-dashboard.onrender.com`)

### Step 2: Generate an API Key (1 minute)

In Windows PowerShell, run:
```powershell
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((1..32 | ForEach-Object { [char][int](Get-Random -Minimum 33 -Maximum 126) } | join '')))
```

Or just use any strong password like: `gloorbot-secret-key-12345-change-this`

### Step 3: Set Environment Variables on Coordinator (2 minutes)

1. Go to https://dashboard.render.com
2. Click **gloorbot-coordinator** service
3. Click **Settings** tab
4. Click **Environment** section
5. **Add these variables**:
   - Name: `CHEAPSKATER_INGEST_URL`
     Value: `https://cheapskater-dashboard.onrender.com/api/ingest/deals`
   - Name: `CHEAPSKATER_INGEST_API_KEY`
     Value: `[paste your generated key from Step 2]`
6. Click **Save**
7. **The service will automatically redeploy** (takes 1-2 minutes)

### Step 4: Set the Same API Key on CheapSkater (2 minutes)

1. Go to https://dashboard.render.com
2. Click **cheapskater-dashboard** service
3. Click **Settings** tab
4. Click **Environment** section
5. **Find or Add this variable**:
   - Name: `CHEAPSKATER_INGEST_API_KEY`
   - Value: `[paste the SAME key from Step 2]`
6. Click **Save**
7. **The service will automatically redeploy**

### Step 5: Verify It's Working (2 minutes)

Wait 2 minutes for both services to redeploy, then:

```bash
# Run the debug script again
python debug_data_flow.py
```

You should now see:
- ✅ Environment variables are set
- ✅ CheapSkater health endpoint returns 200
- ✅ Recent deals showing up in both databases

## Check the Logs to Confirm

### In Coordinator Logs (should see after each scrape):
```
Forwarded 5 deals to Cheapskater: accepted=5
```

### In CheapSkater Logs (should see after deals arrive):
```
Processed 5 deals from gloorbot
```

## Troubleshooting

**Q: Still seeing "CheapSkater returned 404"?**
A: The dashboard might not have redeployed yet. Wait 2-3 minutes and try again.

**Q: Logs don't show "Forwarded X deals to Cheapskater"?**
A: - Check the `CHEAPSKATER_INGEST_URL` is correct (with `/api/ingest/deals` at the end)
   - Make sure you actually sent deals to the coordinator
   - Check coordinator logs for any errors

**Q: Deals in Coordinator but not in CheapSkater?**
A: - Verify the API key matches on both services
   - Check CheapSkater logs for "Invalid API key" errors
   - The ingest endpoint might not be registered (but it should be)

**Q: Nothing happened after waiting?**
A: - The services might be stuck deploying. Try clicking **"Manual Deploy"** on each service

## If Everything Still Doesn't Work

Run this to get detailed debug output:
```bash
cd "C:\Users\User\Documents\GitHub\Telomere\Gloorbot"
python debug_data_flow.py
```

Then check:
1. The **SUMMARY** section at the end
2. The **Environment Variables** section
3. The **Health Check** sections for any errors
4. Post the output in your notes for further analysis

---

## Expected Timeline

- Steps 1-2: 3 minutes
- Steps 3-4: 4 minutes (+ 2-3 min auto redeploy)
- Step 5: 2 minutes

**Total: ~10-15 minutes to get data flowing end-to-end**
