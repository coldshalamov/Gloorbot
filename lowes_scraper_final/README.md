# Lowe's Parallel Scraper - Clean Version
# ========================================
# A robust, resumable, parallel scraper for Lowe's product listings.
# This version uses ephemeral browser contexts (no disk bloat).
#
# USAGE:
#   python run.py
#   python run.py --state WA,OR --workers 5
#   python run.py --state WA --workers 3
#
# OUTPUT:
#   - output/          : JSONL product data per store
#   - logs/            : Worker logs
#   - checkpoints/     : Resume progress files
#
# FEATURES:
#   - Resumable: Workers save progress after each category
#   - Parallel: Multiple Chrome instances scraping different stores
#   - No disk bloat: Uses temp browser profiles that auto-delete
#   - Anti-block: Headful Chrome with human-like behavior
#   - Self-healing: Restarts workers that crash or get blocked
