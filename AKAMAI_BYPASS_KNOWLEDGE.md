# Akamai Bot Manager Bypass - What Works & What Doesn't

## ✅ WHAT WORKS (Confirmed Working Solution)

### 1. **Persistent Browser Profiles** (CRITICAL)
- **Use**: `chromium.launchPersistentContext(profileDir, options)`
- **Why**: Akamai trusts browsers with consistent cookies/history over fresh instances
- **Implementation**: Create one profile per store in `.playwright-profiles/store_XXXX/`
- **Don't**: Use `browser.launch()` + `newContext()` - creates fresh instances that Akamai flags

### 2. **Session Warm-up** (CRITICAL)
- **Always visit homepage FIRST** before navigating to protected pages
- **Add human behavior** on homepage: mouse movements, scrolling, random delays
- **Wait 3-5 seconds** for Akamai's JavaScript challenge to complete
- **Implementation**: See `warmUpSession()` in main.js:698-715

### 3. **Human-like Behavior** (CRITICAL)
- **Mouse movements**: Bezier curve paths with random jitter (not straight lines)
- **Scrolling**: Variable speed, multiple small steps (not instant)
- **Timing**: Random delays between actions (avoid patterns)
- **Implementation**: See `humanMouseMove()` and `humanScroll()` in main.js:663-696
- **When**: After EVERY page navigation

### 4. **Real Chrome Browser** (IMPORTANT)
- **Use**: `channel: 'chrome'`
- **Why**: Chrome has different TLS/JA3 fingerprints than Chromium
- **Don't**: Use Chromium or default Playwright browser

### 5. **Browser Arguments** (IMPORTANT)
```javascript
args: [
  '--disable-blink-features=AutomationControlled',  // Hide webdriver flag
  '--disable-dev-shm-usage',
  '--disable-infobars',
]
```

## ❌ WHAT DOESN'T WORK

### 1. **Fingerprint-injector Alone**
- **Why Failed**: Only masks browser fingerprint, doesn't simulate human behavior
- **Akamai detects**: Lack of mouse movements, scrolling, timing patterns
- **Tested**: Chrome + fingerprint-injector still got blocked

### 2. **Firefox (Even with Docs Recommendation)**
- **Why Failed**: Despite Apify docs saying "Firefox is less common for scraping"
- **Still blocked**: Akamai detects behavioral patterns regardless of browser
- **Tested**: Vanilla Firefox and Firefox + fingerprint-injector both blocked

### 3. **Fresh Browser Instances**
- **Why Failed**: Each new instance has no cookies/history - obvious bot behavior
- **Akamai sees**: Brand new browser visiting product pages directly
- **Tested**: Even with fingerprinting + human behavior, fresh instances blocked

### 4. **Resource Blocking**
- **Don't aggressively block**: Images, fonts, CSS
- **Why**: Real users load these resources - blocking them is a bot signal
- **Only block**: Third-party analytics (Google Analytics, GTM, etc.)

### 5. **Direct Navigation**
- **Don't**: Navigate directly to `/pl/` product listing pages
- **Why**: Real users browse from homepage → category → products
- **Do**: Always visit homepage first, simulate browsing

## 🔍 HOW AKAMAI DETECTS BOTS

1. **Browser Fingerprint**: Canvas, WebGL, AudioContext, Screen - checked via JavaScript
2. **Behavioral Patterns**: Mouse movements, scrolling, click patterns, timing
3. **Session Consistency**: Cookies, browsing history, profile data
4. **TLS Fingerprints**: Different between Chrome, Chromium, Firefox
5. **Navigation Patterns**: Direct access to protected pages vs. natural browsing

## 📝 IMPLEMENTATION CHECKLIST

For any Akamai-protected site:

- [ ] Use `launchPersistentContext()` with store-specific profile directory
- [ ] Visit homepage first and wait 3-5 seconds
- [ ] Simulate mouse movements (10-20 steps with bezier curves)
- [ ] Simulate scrolling (4-8 small increments)
- [ ] Add random delays (1-3 seconds between actions)
- [ ] Use real Chrome browser (`channel: 'chrome'`)
- [ ] Include `--disable-blink-features=AutomationControlled` arg
- [ ] Add human behavior after EVERY page navigation
- [ ] Don't block images/fonts (only third-party analytics)
- [ ] Run non-headless initially to verify bypass works

## 🚫 COMMON MISTAKES TO AVOID

1. **IP Blocking Myth**: User was on mobile carrier IP - it's NOT IP blocks, it's behavioral detection
2. **Proxy Solution Myth**: User is on residential connection - proxies won't fix broken code
3. **"Access Denied" ≠ IP Block**: It's Akamai's JavaScript challenge failing, not network-level blocking
4. **Fingerprinting Alone**: Browser fingerprint masking is not enough - need behavioral simulation
5. **One-Size-Fits-All**: Each anti-bot system is different - test and verify each solution

## 📊 SUCCESS METRICS

When working correctly, you should see:
- **HTTP 200** responses (not 403)
- **Page title**: Shows actual category name (not "Access Denied")
- **Products found**: 15+ ProductCard elements on listing pages
- **Cookies**: `_abck` cookie value contains `~0~` or `~-1~` (challenge states)
- **Multiple pages**: Can navigate through pagination without blocks

## 🔗 Key Files

- **Main implementation**: `apify_actor_seed/src/main.js` (lines 663-783)
- **Working test**: `apify_actor_seed/test_final.js`
- **Documentation**: `RUN_SCRAPER.md`
