# Project Overview
- Purpose: Distributed Lowe's deal scraper with a Render-hosted coordinator and Windows worker app. Worker reuses the PARALLEL Playwright scraper.
- Main components:
  - apps/coordinator: FastAPI coordinator + website + SSE updates (per README).
  - apps/worker: Windows Tkinter GUI worker, supervisor, slot workers, installer build scripts.
  - PARALLEL: Local Playwright scraping engine.
  - tools: diagnostics/analysis scripts.
- Platforms: Windows-focused worker; coordinator hosted on Render (render.yaml).

# Tech Stack
- Python >=3.10
- Playwright (pinned 1.49.1), requests, psutil
- Tkinter GUI (worker)
- FastAPI (coordinator, per README)
