# GLOORBOT SYSTEMATIC DEBUGGING PLAN
# Date: 2025-12-28
# Goal: Find the EXACT configuration that works for Lowe's without blocking

## VARIABLES TO TEST

We have THREE known configurations:
1. PARALLEL (Chrome channel) - WORKS
2. Cheapskater (Chromium + stealth) - WORKS  
3. GloorbotWorker (Chromium + stealth) - BLOCKED

## TEST MATRIX

| Test | Browser | Stealth | Profile | Expected | Actual |
|------|---------|---------|---------|----------|--------|
| A    | Chrome channel | None | Fresh | WORKS (like PARALLEL) | ? |
| B    | Chromium | None | Fresh | ? | ? |
| C    | Chromium | stealth_async | Fresh | WORKS (like Cheapskater) | ? |
| D    | Chromium | hook_playwright_context | Fresh | BLOCKED (old pattern) | ? |
| E    | Chrome channel | stealth_async | Fresh | ? | ? |

## EXECUTION PLAN

### PHASE 1: Baseline Tests (run locally, no build needed)
- [ ] Test A: Chrome channel, no stealth
- [ ] Test B: Chromium, no stealth
- [ ] Test C: Chromium with stealth_async (v0.5.0 pattern)
- [ ] Test D: Chromium with hook_playwright_context (old broken pattern)

### PHASE 2: Determine Working Config
- Whichever test passes = the config we use

### PHASE 3: Apply to Worker
- Update slot_worker.py to match working config
- Push new version
- Build and test

### PHASE 4: End-to-End Validation
- Download installer
- Run on fresh machine
- Verify full scraping works

## NOTES
- Delete test profiles between tests for fresh state
- Record navigator.webdriver value for each test
- Take screenshots of results
