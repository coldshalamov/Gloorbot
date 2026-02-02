# Edit Log

## 2026-02-01
- Fixed false-positive block detection on legitimate titles (e.g., "Robotic Vacuum") by tightening title matching in `PARALLEL/scraper.py`.
- Restricted block detection to explicit "Access Denied" only (per ops) in `PARALLEL/scraper.py`.
