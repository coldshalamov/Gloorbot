# FINAL Seed Package Summary

## ✅ Definitive Seed Package Complete

**Location**: `C:\Github\GloorBot Apify\apify_actor_seed\`

This is the result of collaboration between **Antigravity (Gemini)** and **Codex (GPT)**, optimized for **Claude Opus 4.5**.

---

## 📦 What's Inside (Complete Inventory)

### Core Code (Python Only)
- `src/retailers/lowes.py` - 1,467 lines of battle-tested scraper logic
- `src/retailers/selectors.py` - CSS selectors
- `src/extractors/dom_utils.py` - DOM parsing helpers
- `src/catalog/discover_lowes.py` - URL discovery
- `src/utils/anti_blocking.py` - User-Agent rotation
- `src/utils/normalizers.py` - Data cleaning
- `src/utils/comms.py` - Playwright environment config
- `src/utils/multi_store.py` - URL blocklist & dedupe
- `src/utils/errors.py` - **CRITICAL** Custom exceptions

### Data & Config
- `input/LowesMap.txt` - Store IDs (source of truth)
- `catalog/*.yml` - Category definitions
- `.actor/actor.json` - Apify platform config
- `.actor/input_schema.json` - Input UI schema
- `.actor/dataset_schema.json` - Output validation schema
- `Dockerfile` - Container definition
- `requirements.txt` - Dependencies

### Documentation (Tiered)

#### **Tier 1: Start Here** (For Opus 4.5)
- **`CLAUDE_ONE_SHOT_CONTEXT.md`** ⭐ Master guide with snippets, architecture, checklist
- **`FINAL_AUDIT_REPORT.md`** ⚠️ Critical gotchas (import paths, logging)
- **`CRITICAL_FIXES_20251204.md`** 🔥 Crash/pickup filter bugs

#### Tier 2: Reference
- `CONTEXT_FOR_CLAUDE.md` - Apify SDK patterns
- `LOWES_URL_DISCOVERY_GUIDE.md` - How categories work
- `APIFY_ACTOR_CONTEXT.md` - Actor packaging notes

#### Tier 3: Background
- `CRAWLER_READY.md` - Original scraper status
- `EXHAUSTIVE_LOWES_COVERAGE.md` - Category coverage
- `AUTO_SCRAPER_MONITORING.md` - Monitoring patterns
- `README.md` - Seed overview
- `Akamai Bot Academy.txt` - Anti-bot tactics (12k lines)

### Third-Party Examples
- `third_party/apify-playwright-example.py` - Playwright + Apify pattern
- `third_party/proxy_rotation_example.py` - Session locking example
- `third_party/THIRD_PARTY_SNIPPETS.md` - Distilled snippets
- `third_party/*-README.md` - SDK/library docs

---

## 🎯 Prompt for Claude Opus 4.5

Use this exact prompt:

```
You are building a production Apify Actor to scrape Lowe's stores (WA/OR focus) while surviving Akamai anti-bot defenses.

**Start by reading these files IN ORDER:**
1. CLAUDE_ONE_SHOT_CONTEXT.md - Architecture, snippets, checklist
2. FINAL_AUDIT_REPORT.md - Critical integration issues
3. CRITICAL_FIXES_20251204.md - Known bugs to preserve fixes for

**Your mission:**
Build `src/main.py` using the Apify SDK (`async with Actor:`) that:
- Imports and uses the scraping logic from `src/retailers/lowes.py`
- Uses residential proxies with session locking (see context doc)
- Runs headful Playwright with playwright-stealth
- Reads input from `.actor/input_schema.json`
- Outputs to Dataset per `.actor/dataset_schema.json`

**Critical constraints:**
- Python 3.12 only (NOT Node.js)
- Update ALL imports from `from app.*` to `from src.*`
- Use `Actor.log` (NOT `logging_config.py`)
- DO NOT refactor the pickup filter loop or crash detection
- Call `_apply_pickup_filter_on_page` on EVERY pagination page

**You have all the code you need in `src/`. Your job is to wire it into the Apify Actor framework.**

Good luck.
```

---

## 🔍 What We Removed (Noise Filter)

- ❌ Node/TypeScript artifacts (`fingerprint-injector.ts`, `got-scraping`)
- ❌ Local launchers (`.bat`, `.sh`, `launcher_gui.py`)
- ❌ Development artifacts (`logs/`, `outputs/`, `.venv/`, `.pyc`)
- ❌ UI/Dashboard code (`dashboard.py`, `static/`, `templates/`)
- ❌ Unrelated retailers (`homedepot.py`)
- ❌ Cheapskater-specific logging (`logging_config.py` - incompatible with Apify)

---

## 🤝 Collaboration Notes

**Antigravity's Contributions:**
- Identified missing `errors.py` dependency
- Created import path migration guide
- Emphasized session locking for proxies
- Created master context document

**Codex's Contributions:**
- Exhaustive doc extraction (CRAWLER_READY, EXHAUSTIVE_LOWES_COVERAGE)
- Third-party example synthesis (apify-playwright-example.py)
- Comprehensive README distillation
- Token-efficient organization

**Combined Result:**
A one-shot seed package with:
- Complete working code (no missing dependencies)
- Integration guidance (import paths, logging patterns)
- Architectural constraints (Python + Playwright + Apify SDK)
- Freedom for Opus to design optimal wiring

---

## ✅ Verification Checklist

- [x] All `lowes.py` dependencies present
- [x] Custom exceptions (`errors.py`) included
- [x] Import path migration documented
- [x] Logging pattern change documented
- [x] Apify config files (actor.json, schemas) created
- [x] Docker base image specified (apify/actor-python-playwright:3.12)
- [x] Dependencies listed (requirements.txt)
- [x] Anti-bot tactics documented (Akamai Bot Academy)
- [x] Critical bugs documented (CRITICAL_FIXES)
- [x] Third-party examples extracted

---

**Status**: 🟢 **READY FOR OPUS 4.5**

The seed package is complete, coherent, and optimized for a one-shot build by the most capable coding model available.
