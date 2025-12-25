# Akamai Unblock Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Identify and fix the specific anti-bot signals in this repo so the Lowe's actor reliably avoids Akamai blocks.

**Architecture:** Use a diagnostic-first approach: validate proxy usage, stabilize fingerprinting, verify Akamai script loading, and iterate with minimal test runs. Changes are applied in small steps with explicit verification after each change.

**Tech Stack:** Python, Playwright, Apify SDK, playwright-stealth, PowerShell test runs.

---

### Task 1: Read diagnostics and deployment docs

**Files:**
- Read: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\BLOCKING_DIAGNOSIS_20251215.md`
- Read: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\DEPLOYMENT_GUIDE.md`
- Read: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\third_party\THIRD_PARTY_SNIPPETS.md`

**Step 1: Summarize the constraints that cause Akamai blocks**
- Extract concrete requirements (proxy use, headful, anti-fingerprinting order, Akamai script allowlist).

**Step 2: Identify which requirements are enforced in code**
- Cross-check against `src/main.py` and `app/playwright_env.py`.

**Step 3: Record any mismatches or gaps**
- Create a short checklist in this plan file under a new section “Gap Checklist”.

**Step 4: Verify the checklist is actionable**
- Ensure each gap maps to a concrete code change or test.

**Step 5: Commit**
```bash
git add docs/plans/2025-12-23-akamai-unblock.md
git commit -m "docs: add akamai unblock implementation plan"
```

---

### Task 2: Add diagnostic logging (no behavior changes)

**Files:**
- Modify: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py`

**Step 1: Write a minimal diagnostic log plan**
- Log: proxy status, proxy host, UA used, timezone/locale, Akamai script allowlist hits.

**Step 2: Implement logs only (no logic changes)**
- Add logs around proxy creation and context creation.

**Step 3: Run a minimal local test**
```powershell
$env:CHEAPSKATER_RANDOM_UA="0"
python C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
```
Expected: Log shows proxy status, UA, and Akamai requests not blocked.

**Step 4: Capture whether Access Denied appears**
- Note the exact URL and status in logs.

**Step 5: Commit**
```bash
git add C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
git commit -m "chore: add anti-bot diagnostic logging"
```

---

### Task 3: Validate fingerprint stability per session

**Files:**
- Modify: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py`

**Step 1: Add a small JS snippet to compute a fingerprint hash**
- Example: hash of canvas, WebGL vendor/renderer, audio fingerprint, screen sizes.

**Step 2: Log the fingerprint hash before and after a category navigation**
- Hash should remain constant within the same context.

**Step 3: Run a minimal local test**
```powershell
$env:CHEAPSKATER_RANDOM_UA="0"
python C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
```
Expected: Hash is stable across multiple pages within one store.

**Step 4: If hash changes, fix the source of drift**
- Update injection scripts to use context-stable values.

**Step 5: Commit**
```bash
git add C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
git commit -m "chore: log fingerprint stability"
```

---

### Task 4: Verify UA and client hints consistency

**Files:**
- Modify: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py`

**Step 1: Ensure UA randomization is opt-in only**
- Default should be Chromium’s native UA to match client hints.

**Step 2: Add logging for UA and any override flags**

**Step 3: Test with UA randomization off**
```powershell
$env:CHEAPSKATER_RANDOM_UA="0"
python C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
```

**Step 4: Test with UA randomization on (optional)**
```powershell
$env:CHEAPSKATER_RANDOM_UA="1"
python C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
```

**Step 5: Commit**
```bash
git add C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
git commit -m "chore: clarify ua randomization"
```

---

### Task 5: Confirm Akamai scripts are never blocked

**Files:**
- Modify: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py`

**Step 1: Add log in `setup_request_interception` for every blocked request**
- Include URL and reason (type vs pattern match).

**Step 2: Add log for every `NEVER_BLOCK_PATTERNS` match**
- Confirm Akamai paths pass through.

**Step 3: Run the minimal test**
```powershell
python C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
```
Expected: Akamai URLs logged as allowed.

**Step 4: Commit**
```bash
git add C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
git commit -m "chore: log request blocking decisions"
```

---

### Task 6: Proxy verification (local + Apify)

**Files:**
- Modify: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py`
- Read: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\DEPLOYMENT_GUIDE.md`

**Step 1: Add a simple IP check before crawling (optional toggle)**
- When `CHEAPSKATER_PROXY_DIAGNOSTIC=1`, open `https://lumtest.com/myip.json` and log IP.

**Step 2: Run test with proxy diagnostics on**
```powershell
$env:CHEAPSKATER_PROXY_DIAGNOSTIC="1"
python C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
```
Expected: IP differs from local IP when proxy is enabled.

**Step 3: Commit**
```bash
git add C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
git commit -m "chore: add proxy diagnostic"
```

---

### Task 7: Iterate until Access Denied disappears

**Files:**
- Modify: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py`

**Step 1: After each test, record status**
- “Access Denied” title present? Which URL? At which page?

**Step 2: If blocked, adjust only one variable at a time**
- Example variables: proxy on/off, UA randomization, fingerprint noise values, delays.

**Step 3: Repeat minimal test**

**Step 4: Stop once 2 successful pages are fetched without Access Denied**

**Step 5: Commit**
```bash
git add C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\src\main.py
git commit -m "fix: reduce akamai blocks with verified adjustments"
```

---

### Task 8: Validate on Apify with residential proxy

**Files:**
- Modify: `C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\.actor\input_schema.json`
- Run: Apify test run

**Step 1: Use a tiny input (1 store, 1 category, 2 pages)**

**Step 2: Confirm no blocks and data extracted**

**Step 3: Document final settings**
- Add a brief note to `README.md` about required proxy settings.

**Step 4: Commit**
```bash
git add C:\Users\User\Documents\GitHub\Telomere\Gloorbot\apify_actor_seed\README.md
git commit -m "docs: document proxy + anti-bot settings"
```

---

## Gap Checklist
- [ ] Proxy used and confirmed via IP check
- [ ] Headful Chromium (no headless) confirmed in logs
- [ ] UA / client hints consistent (Chromium default unless explicitly randomized)
- [ ] Fingerprint stable per context (hash matches across two reads)
- [ ] Akamai scripts never blocked (/_sec/, /akam allowed)
- [ ] 2+ pages fetched without Access Denied
- [ ] Apify run successful with residential proxy
