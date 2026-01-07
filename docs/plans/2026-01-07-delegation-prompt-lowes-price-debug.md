# Delegation Prompt: Lowe’s Wrong-Price Debugging (Copy/Paste)


---

You are debugging persistent wrong-price extraction in a Lowe’s scraper. We sometimes post deals where the “now” price is something unrelated like `$125` (likely from financing text like `$125/mo`), and `was_price` is also scrambled.

Repo context:
- Price extraction is in `PARALLEL/scraper.py`, function `extract_prices_from_card()` and also a JS `page.evaluate` block used for “near-me” DOM scoping.
- Worker-side parsing/sanity checks are in `apps/worker/src/gloorbot_worker/slot_worker.py`.

Your tasks:
1) Open a real Lowe’s example (start with SKU `1003010946`) in Chrome with DevTools.
   - Confirm where “Actual Price” and “Was Price” appear (aria-labels, data-selectors, and text splits).
   - Identify *every* other `$` amount on the page/card (financing, savings, credit offers, shipping thresholds).
2) Confirm DOM structure for `/pl/` product cards:
   - Is `div.tile_group` a card or a row container?
   - Are multiple products split by `data-tile`? If so, does price/title share `data-tile`?
3) For each found pattern, provide:
   - The minimal reliable selector/attribute strategy
   - A minimal HTML snippet reproducing the pattern (offline fixture)
   - A failure mode description (“this is how we’d accidentally read `$125/mo` as product price”)

Diagnostics already available:
- Set `GLOORBOT_PRICE_DIAGNOSTICS=1` to write JSONL trace events (source attempts, aria-label strings used/rejected).
- Set `GLOORBOT_DEAL_DIAGNOSTICS=1` to log why each candidate becomes a deal or gets dropped.

Deliverables:
- A prioritized list of remaining likely failure modes
- 3–8 offline HTML fixtures we should add as tests
- Any small, focused code diffs to improve correctness or diagnostics

Constraints:

- Do not propose “scan entire card text for dollars” as a fallback.

