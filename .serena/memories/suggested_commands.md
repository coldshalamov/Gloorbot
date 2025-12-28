# Suggested Commands (Windows)
## Worker dev run
- cd apps/worker
- python -m venv .venv
- .\.venv\Scripts\pip install -e .
- .\.venv\Scripts\python -m playwright install chromium
- $env:GLOORBOT_COORDINATOR_URL="http://127.0.0.1:8000"
- .\.venv\Scripts\python -m gloorbot_worker

## Packaging
- GitHub Actions workflow builds WorkerSetup.exe (see .github/workflows/worker-build.yml)
- Inno Setup script: apps/worker/installer/worker.iss
