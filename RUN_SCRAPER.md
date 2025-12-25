# How to Run the Lowe's Scraper

## Current Status: WORKING

The Akamai bypass is now working using persistent browser profiles and human-like behavior simulation.

## Quick Test

Run this to verify the bypass is working:

```bash
cd apify_actor_seed
node test_final.js
```

You should see:
- "RESULT: SUCCESS!"
- Product counts showing 15+ ProductCard elements
- Page text showing Lowe's content

## Running the Full Scraper

```bash
cd apify_actor_seed
node src/main.js
```

The scraper will:
1. Create a persistent browser profile per store
2. Warm up each session by visiting the homepage first
3. Simulate human behavior (mouse movements, scrolling)
4. Navigate to each category and extract products
5. Apply "Pickup Today" filter where possible

## How the Akamai Bypass Works

The solution uses these techniques:

1. **Persistent Browser Profile**: Akamai trusts browsers with consistent profiles over fresh instances. The scraper creates profiles in `.playwright-profiles/store_XXXX/`

2. **Real Chrome Browser**: Uses the actual Chrome browser (not Chromium) which has different TLS fingerprints that are harder to detect

3. **Session Warm-up**: Visits the homepage first and simulates human behavior before navigating to protected product pages

4. **Human-like Behavior**: Simulates realistic mouse movements and scrolling between page loads

5. **Proper Timing**: Adds random delays between actions to avoid detection patterns

## Environment Variables

```bash
# Disable persistent profile (not recommended)
set CHEAPSKATER_PERSISTENT_PROFILE=0

# Use Chromium instead of Chrome (not recommended)
set CHEAPSKATER_BROWSER_CHANNEL=chromium
```

## Troubleshooting

### Still getting "Access Denied"

1. Delete the profile directory: `rmdir /s .playwright-profiles`
2. Run the test again - it will create a fresh profile

### Chrome not found

Install Google Chrome from https://www.google.com/chrome/

### Timeout errors

- Network might be slow, try again
- The warm-up phase takes 5-10 seconds per store

### No products found

- The page loaded but selectors might have changed
- Check the screenshot files for visual debugging

## Deploy to Apify

```bash
cd apify_actor_seed
apify push
```

Then run from the Apify Console. The actor will work with Apify's infrastructure.
