# Lowe's Scraper Actor Roadmap

This repository contains multiple versions of the Lowe's scraper. This document identifies the production-ready code and its capabilities.

## 🏁 The Production Actor (The "Smart" One)
**Location**: `lowes-apify-actor/`

This is the version you should use for deployment. It has been audited and optimized for Akamai bypass and cost efficiency.

### Why this is the "Working Actor":
- **Akamai Evasion**: Uses Python Playwright with headful mode and advanced fingerprint noise injection (Canvas, WebGL, AudioContext).
- **Anti-Blocking**: Native support for **Residential Proxies** with session locking.
- **Cost optimized**: Blocks non-essential resources (images, fonts, media) to save 60-70% on bandwidth costs.
- **Reliable**: Designed for 4GB memory environments.

## 🛠️ Folder Structure
- `lowes-apify-actor/`: **PRODUCTION**. Consolidated package for Apify.
- `apify_actor_seed/`: Development seed. Contains both JS and Python versions (legacy).
- `local_scraper.py`: Designed for running on a local machine with a home IP.
- `LowesMap.txt`: Root database of all department URLs and store IDs.

## 🚀 Key Deployment Files
- `lowes-apify-actor/src/main.py`: Main entry point.
- `lowes-apify-actor/DEPLOYMENT_GUIDE.md`: Step-by-step setup for Apify Console.

## 📋 Capabilities for Full Crawl
The production actor is being updated to support:
1. **Full Coverage**: Iterates through ALL categories in `LowesMap.txt`.
2. **All Stores**: Covers all 49 stores in WA and OR.
3. **Infinite Pagination**: Scrapes every single product listing in every category.
4. **State Persistence**: Supports resuming from failure by tracking progress in Apify's Key-Value Store.

---
*Maintained by Antigravity AI*
