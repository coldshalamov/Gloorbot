# Edit Log

## 2026-02-01
- Fixed false-positive block detection on legitimate titles (e.g., "Robotic Vacuum") by tightening title matching in `PARALLEL/scraper.py`.
- Restricted block detection to explicit "Access Denied" only (per ops) in `PARALLEL/scraper.py`.
- Added max backoff duration so block-based slot limiting expires and restores full slots (default 30 minutes) in `apps/worker/src/gloorbot_worker/supervisor.py`.
- Installer now defaults to full clean on install and force-kills the worker on uninstall in `apps/worker/installer/worker.iss`.
- GUI startup removes stale profiles after a crashed run (only when no worker processes are active) in `apps/worker/src/gloorbot_worker/gui.py`.
