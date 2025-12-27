# 🔍 WHY CHEAPSKATER DEBUG WORKS BUT APIFY ACTOR GETS BLOCKED

## Key Differences Analysis

### ✅ WORKING: Cheapskater Debug (`parallel_scraper.py`)

**Line 229**: `apply_stealth(p)` - Called BEFORE browser launch
```python
async with async_playwright() as p:
    apply_stealth(p)  # ✅ Hooks Playwright context FIRST
    ...
    browser = await p.chromium.launch(**launch_opts)
```

**Browser Launch Args** (from `playwright_env.py`):
```python
args = [
    "--disable-blink-features=AutomationControlled",  # ⚠️ Present but works
    "--disable-dev-shm-usage",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-infobars",
    "--lang=en-US",
    "--no-default-browser-check",
    "--start-maximized",
    "--window-size=1440,960",
]

channel = os.getenv("CHEAPSKATER_BROWSER_CHANNEL", "chromium")  # ✅ Defaults to "chromium"
```

**Key Points**:
- ✅ `apply_stealth(p)` called BEFORE browser launch
- ✅ Channel defaults to `"chromium"` (not Chrome)
- ⚠️ Has custom args (but works because stealth is applied first)
- ✅ No custom fingerprint injection (Canvas/WebGL/Audio)

---

### ❌ BROKEN: Apify Actor (`apify_actor_seed/src/main.py`)

**Lines 1350-1362**: Stealth created AFTER browser launch
```python
async with async_playwright() as pw:
    browser = None
    launch_opts = {
        "headless": False,
        "args": _launch_args(),  # ❌ Custom args
    }
    channel = browser_channel()  # ❌ Might use Chrome
    if channel:
        launch_opts["channel"] = channel
    browser = await pw.chromium.launch(**launch_opts)  # ❌ Launched FIRST
    
    stealth = Stealth()  # ❌ Created AFTER browser launch
```

**Problems**:
1. ❌ Browser launched BEFORE stealth is applied
2. ❌ `browser_channel()` might return `"chrome"` (triggers Akamai)
3. ❌ `_launch_args()` adds custom args that might trigger detection
4. ❌ Stealth is created but never hooked to Playwright context
5. ❌ Has custom fingerprint injection code (Canvas/WebGL/Audio) that triggers Akamai

---

## 🎯 THE CRITICAL DIFFERENCE

### Cheapskater Debug:
```python
async with async_playwright() as p:
    apply_stealth(p)  # ← Hooks BEFORE launch
    browser = await p.chromium.launch(...)
```

### Apify Actor:
```python
async with async_playwright() as pw:
    browser = await pw.chromium.launch(...)  # ← Launches FIRST
    stealth = Stealth()  # ← Created AFTER (never hooked!)
```

---

## 📊 DETAILED COMPARISON TABLE

| Feature | Cheapskater Debug | Apify Actor | Impact |
|---------|-------------------|-------------|--------|
| **Stealth Hook Timing** | ✅ BEFORE browser launch | ❌ AFTER browser launch | **CRITICAL** |
| **Stealth Applied** | ✅ `apply_stealth(p)` | ❌ Never hooked | **CRITICAL** |
| **Browser Channel** | ✅ `"chromium"` (default) | ❌ Might use `"chrome"` | **HIGH** |
| **Custom Args** | ⚠️ Has args (but works) | ❌ Has args (breaks) | **MEDIUM** |
| **Fingerprint Injection** | ✅ None | ❌ Canvas/WebGL/Audio | **HIGH** |
| **Page-level Stealth** | ✅ Not needed (context-level) | ❌ Applied to pages | **MEDIUM** |

---

## 🔧 WHY CHEAPSKATER DEBUG WORKS

1. **Stealth is hooked to Playwright context** - This modifies the browser's behavior at the deepest level
2. **Uses default Chromium** - Not Chrome channel which has different fingerprints
3. **No custom fingerprint injection** - Relies solely on playwright-stealth
4. **Timing is correct** - Stealth applied before any browser operations

---

## 🚨 WHY APIFY ACTOR FAILS

1. **Stealth never hooked** - `Stealth()` object created but `hook_playwright_context()` never called
2. **Browser launched first** - By the time stealth is created, browser is already running
3. **Might use Chrome channel** - If `browser_channel()` returns `"chrome"`, triggers Akamai
4. **Custom fingerprint injection** - The Canvas/WebGL/Audio noise injection is detectable by Akamai
5. **Wrong stealth application** - Applying to individual pages doesn't work as well as context-level

---

## ✅ THE FIX

### Current (Broken):
```python
async with async_playwright() as pw:
    browser = await pw.chromium.launch(**launch_opts)
    stealth = Stealth()  # Created but never used!
```

### Fixed (Like Cheapskater):
```python
async with async_playwright() as pw:
    stealth = Stealth()
    stealth.hook_playwright_context(pw)  # Hook BEFORE launch!
    browser = await pw.chromium.launch(headless=False)  # Simple!
```

---

## 💡 ADDITIONAL INSIGHTS

### Why Custom Args Work in Cheapskater But Not Apify

Cheapskater Debug has custom args like `--disable-blink-features=AutomationControlled`, but it still works because:

1. **Stealth is applied first** - This patches Playwright's internals before the browser starts
2. **The hook modifies browser behavior** - Even with custom args, stealth overrides detection vectors
3. **Order matters** - Hook → Launch → Navigate works; Launch → Hook doesn't

### Why Apify Actor's Fingerprint Injection Backfires

The Apify actor has functions like:
- `inject_canvas_noise()`
- `inject_webgl_noise()`
- `inject_audio_noise()`

These are **detectable** by Akamai because:
- They inject JavaScript into pages
- The noise patterns can be fingerprinted
- Akamai can detect the injection itself
- playwright-stealth already handles this better at a lower level

---

## 🏁 CONCLUSION

**The Apify actor fails because:**
1. Stealth is never hooked to Playwright context
2. Browser is launched before stealth is ready
3. Custom fingerprint injection triggers Akamai
4. Might use Chrome channel instead of Chromium

**Cheapskater Debug works because:**
1. Stealth is hooked BEFORE browser launch
2. Uses default Chromium channel
3. No custom fingerprint injection
4. Correct timing and order of operations

**The fix is simple:** Move stealth hook before browser launch and remove custom fingerprint code.

---

*This explains why your local Cheapskater Debug works perfectly while the Apify actor gets blocked constantly.*
