# Lowe's Parallel Scraper - Final Version
# ========================================
# A robust, resumable, parallel scraper for Lowe's product listings.
#
# USAGE:
#   python orchestrator.py --state WA --max-workers 5
#   python orchestrator.py --state WA,OR --max-workers 5
#   python orchestrator.py --all-stores --max-workers 5
#
# FILES:
#   - orchestrator.py    : Main entry point, manages worker processes
#   - worker.py          : Single-store scraper with resume support
#   - scraper_core.py    : Playwright browser logic (from apify_actor_seed)
#   - urls.txt           : Store + Category URLs (copy of LowesMap_Final_Pruned.txt)
#   - output/            : JSONL output files per store
#   - logs/              : Worker logs
#   - checkpoints/       : Resume progress files
#
# FEATURES:
#   - Resumable: Workers save progress after each category
#   - Parallel: Multiple Chrome instances scraping different stores
#   - Anti-block: Headful Chrome with human-like behavior
#   - Self-healing: Restarts workers that crash or get blocked
