# Solution: Transfer Working Browser Profile from Laptop to PC

## The Problem

Your laptop scraper works because it has an **established browser profile** that Lowe's/Akamai trusts.

When you transferred the code to your PC, the browser profile wasn't included (or didn't transfer correctly), so your PC is creating a **fresh profile** that Akamai immediately flags as suspicious and blocks.

## The Solution

Transfer the working browser profile from your laptop to your PC.

### On Your Laptop:

1. Navigate to your working Cheapskater directory
2. Find the `.playwright-profile` folder (it might be hidden)
3. Create a zip of just this folder:

   **Windows PowerShell:**
   ```powershell
   cd path\to\your\working\Cheapskater
   Compress-Archive -Path .playwright-profile -DestinationPath browser-profile.zip
   ```

   **Or use 7-Zip/WinRAR** to zip the `.playwright-profile` folder

4. The zip should be several MB (maybe 10-50MB) if it contains a real profile
   - If it's tiny (< 1MB), the profile might be empty or missing

5. Transfer `browser-profile.zip` to your PC via:
   - USB drive
   - Cloud storage (Dropbox, Google Drive, OneDrive)
   - Network share
   - Email (if small enough)

### On Your PC:

1. Navigate to your Cheapskater directory:
   ```
   cd "C:\Users\User\Documents\cheapskater debug\Cheapskater_Complete\Cheapskater"
   ```

2. Extract the profile:
   ```powershell
   # Make sure you're in the Cheapskater directory
   Expand-Archive -Path browser-profile.zip -DestinationPath . -Force
   ```

3. Verify the profile exists:
   ```powershell
   ls .playwright-profile
   ```
   You should see folders like `chromium`, `Default`, etc.

4. Run the scraper:
   ```batch
   launch_parallel_all_depts.bat
   ```

## Why This Works

Akamai bot detection uses **browser fingerprinting** and **behavioral analysis**:

### What Gets Stored in Browser Profiles:

1. **Cookies** - Including session cookies, tracking cookies, and Lowe's store preferences
2. **localStorage** - Client-side data Lowe's stores
3. **sessionStorage** - Temporary session data
4. **Cache** - Images, scripts, stylesheets from previous visits
5. **IndexedDB** - Client-side database data
6. **Service Workers** - Background scripts
7. **Permissions** - Granted permissions (location, notifications, etc.)
8. **Browsing History** - Visited URLs and timestamps
9. **TLS Session Cache** - SSL/TLS connection state

### How Akamai Detects Bots:

- **Fresh profiles** = No history, no cookies, no cache = SUSPICIOUS
- **Established profiles** = Cookies from previous visits, cache hits, normal browsing patterns = TRUSTED

Your laptop profile has:
- ✅ Visited Lowe's many times
- ✅ Set store preferences
- ✅ Normal browsing behavior
- ✅ Cookies and session data
- ✅ **Trust score built up over time**

Your PC profile has:
- ❌ Never visited Lowe's
- ❌ No cookies or cache
- ❌ Looks like a brand new automated browser
- ❌ **Immediately flagged as bot**

## Alternative Solution: "Warm Up" a Profile on Your PC

If you can't transfer the profile from your laptop, you can manually create a trusted profile:

1. **Launch the scraper in headed mode** (you can watch the browser)
2. **Before it starts scraping**, manually browse Lowe's:
   - Visit homepage
   - Search for a few products
   - Click into product pages
   - Set your store location
   - Browse a few categories
   - Spend 5-10 minutes browsing naturally
3. **Close the browser properly** (don't force kill it)
4. **Repeat this a few times over several days** to build trust
5. **Then try scraping** - it should work better

## Testing the Transfer

After transferring the profile, run this test:

```bash
cd "C:\Users\User\Documents\GitHub\Telomere\Gloorbot"
python test_mobile_store_page.py
```

If it shows "Access Denied" on the category page, the profile transfer didn't work or isn't being used correctly.

## Technical Note: Why Mobile Emulation Alone Isn't Enough

I found that the working scraper uses **mobile device emulation** (iPhone, Pixel, etc.), which helps but **isn't sufficient by itself**. My tests with mobile emulation still got blocked because they were using fresh profiles.

The combination needed is:
1. ✅ Mobile device emulation (done by parallel_scraper.py)
2. ✅ playwright-stealth (done)
3. ✅ Slow motion timing (done)
4. ✅ **TRUSTED BROWSER PROFILE** ← This is the missing piece on your PC

## Verification

To verify the profile is being used:

1. Check that `.playwright-profile` exists in your Cheapskater directory
2. Check that it contains folders (not empty):
   ```bash
   ls .playwright-profile/chromium/Default
   ```
   Should show files like `Cookies`, `History`, `Local Storage`, etc.

3. Run the scraper and watch for "Store context set" messages in the logs

If the profile is there and it STILL gets blocked, the profile might be:
- Corrupted during transfer
- Machine-specific (less common but possible)
- Incompatible with different Playwright/Chromium versions

In that case, you'll need to manually "warm up" a new profile on your PC.
