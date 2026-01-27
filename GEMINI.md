# GEMINI.MD - Agent Instructions for Gloorbot

## The Mission: Build the Swarm
You are working on **Gloorbot**, a distributed scraping system designed to find hidden clearance deals at Lowe's.

### The Core Loop
1. **GitHub Actions** builds the `WorkerSetup.exe` from `apps/worker/`.
2. **Users** download this worker from the **Coordinator** website (`gloorbot-coordinator.onrender.com`).
3. **The Swarm** runs on users' PCs, scraping data and sending it back to the mothership.
4. **Cheapskater** (`cheapskater.onrender.com`) displays the deals.

### File Structure Truths
- `apps/worker/` is the **Client**.
- `apps/coordinator/` is the **Server**.
- `PARALLEL/scraper.py` is the **Shared Brain** (logic used by both, but primarily the worker).
- `*.py` in the root are **Ghosts** (legacy scripts, do not touch unless asked).

### Rules of Engagement
1. **Do not create random scripts in root.** Use `apps/worker` or `apps/coordinator` for features.
2. **Respect the build pipeline.** Changes to `apps/worker` only go live when a new git tag (`v*`) is pushed.
3. **The zip file is a build artifact.** `GloorbotWorker.zip` contains the output of the build process (PyInstaller folder). It is useful for verifying contents but is not the source code. The end-user installer is `WorkerSetup.exe`.

### How to Verify
- Check `apps/coordinator/data/urls.txt` for the seed list.
- Check `.github/workflows/worker-build.yml` to see how the sausage is made.
- Check `CLAUDE.md` for the latest architectural map.
