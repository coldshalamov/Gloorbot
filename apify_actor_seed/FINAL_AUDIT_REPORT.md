# Final Audit Report: Missing Pieces Found

## ✅ Critical Files Added

### 1. **`src/utils/errors.py`** (COPIED)
**Why Critical**: `lowes.py` imports three custom exceptions:
- `PageLoadError` - Raised when Akamai blocks or page fails
- `StoreContextError` - Raised when store selection fails  
- `SelectorChangedError` - Raised when Lowe's changes their HTML

These exceptions have rich context (url, zip_code, category) that helps debugging.

### 2. **Missing Logging Setup**
The original `logging_config.py` is Windows-specific (forces UTF-8, uses local file handlers). 

**For Apify**: Use `Actor.log` instead:
```python
from apify import Actor

# Inside async with Actor:
Actor.log.info("Message")
Actor.log.error("Error")
```

**Decision**: Do NOT copy `logging_config.py`. Tell Opus to use `Actor.log` exclusively.

---

## 📋 Integration Gaps Identified

### Gap 1: Import Path Conflicts
The existing code uses `from app.* import ...` but the Actor structure is `from src.* import ...`.

**Fix Needed**: Opus must update all imports in `lowes.py`:
```python
# OLD (Cheapskater)
from app.errors import PageLoadError
from app.selectors import CARD

# NEW (Actor)
from src.utils.errors import PageLoadError
from src.retailers.selectors import CARD
```

### Gap 2: Example Actor Main Loop
The Apify docs example I found uses `Apify Client` (for external calls), not `Actor` SDK.

**Better Pattern** (synthesized from SDK README + your code):
```python
import asyncio
from apify import Actor
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def main():
    async with Actor:
        # Actor.log is automatically configured
        Actor.log.info("Starting Lowes Actor")
        
        # Get input
        actor_input = await Actor.get_input() or {}
        
        # Setup proxy
        proxy_config = await Actor.create_proxy_configuration()
        
        # Scrape loop
        results = []
        # ... scraping logic ...
        
        # Push all at once or incrementally
        await Actor.push_data(results)  # or loop: await Actor.push_data(item)

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 🎯 Final Recommendations for Opus 4.5

### DO Include:
1. ✅ All current seed files
2. ✅ `src/utils/errors.py` (just added)
3. ✅ `CLAUDE_ONE_SHOT_CONTEXT.md` (master guide)

### DO NOT Include:
1. ❌ `logging_config.py` (use `Actor.log` instead)
2. ❌ `config.yml` (Actor uses `input_schema.json`)
3. ❌ Full Apify docs (too much noise)

### Add to Context Document:
**New Section: "Import Path Migration"**
```markdown
## Import Path Updates Required

When using code from `src/retailers/lowes.py`, update these imports:

| Old Import (Cheapskater) | New Import (Actor) |
|--------------------------|-------------------|
| `from app.errors import ...` | `from src.utils.errors import ...` |
| `from app.selectors import ...` | `from src.retailers.selectors import ...` |
| `from app.extractors.dom_utils import ...` | `from src.extractors.dom_utils import ...` |
| `from app.logging_config import get_logger` | `from apify import Actor` (use `Actor.log`) |
| `LOGGER = get_logger(__name__)` | Remove (use `Actor.log` directly) |
```

**New Section: "Logging Pattern"**
```markdown
## Logging in Apify Actors

Do NOT use `logging_config.py`. Use `Actor.log` instead:

```python
# Inside async with Actor:
Actor.log.info(f"Scraping store {store_id}")
Actor.log.warning(f"Pickup filter not found on {url}")
Actor.log.error(f"Crash detected: {error}")
```
```

---

## 🤔 Philosophy for Opus 4.5

Since Opus 4.5 is more capable than me, I should:
1. **Give it the complete working code** (`lowes.py`, `errors.py`, etc.)
2. **Point out the integration gaps** (import paths, logging)
3. **Provide the architectural constraints** (Python, Playwright, Apify SDK)
4. **Let it design the optimal wiring** (how to connect the pieces)

**Do NOT**: Over-specify the `main.py` implementation. Opus might find a better pattern than my example.

---

## Final Seed Status

**COMPLETE** ✅

The seed package now contains:
- All working code (1,467-line `lowes.py`, helpers, selectors)
- All critical docs (CRITICAL_FIXES, URL_DISCOVERY, Akamai Academy)
- All dependencies (`requirements.txt`)
- All data (`LowesMap.txt`, catalog YAMLs)
- Integration guidance (`CLAUDE_ONE_SHOT_CONTEXT.md`)
- Error handling (`errors.py`)

**Ready for Opus 4.5**.
