# Investigation Findings: Why does the Worker get blocked while PARALLEL “works”?

Date: 2025-12-28

This document is a *codebase investigation* comparing the two execution paths and enumerating anything that could plausibly change how Lowe’s/Akamai evaluates the session.

I’m intentionally not proposing a “fix” here—only evidence, deltas, and experiments to validate hypotheses.

---

## 0) TL;DR (highest‑signal differences found)

**Most important finding:** The Worker’s *orchestration* (coordinator task ordering + multi‑slot behavior + profile partitioning) is **not equivalent** to the PARALLEL runner’s orchestration, even if both ultimately call the same `PARALLEL/scraper.py` functions.

Ranked hypotheses (with code evidence below):

1) **Coordinator task seeding + leasing creates “store clustering”** at startup (lots of tasks for the same store handed out first), which makes multiple fresh sessions hammer the same store/category patterns early.  
   - Seeding inserts tasks in nested loops: store → categories (`apps/coordinator/coordinator_app/seed.py:63-78`).  
   - Leasing picks the next task by “oldest/never completed” then `id` (`apps/coordinator/coordinator_app/web.py:241-244`).  
   - Implication: At the beginning of a run, **the earliest store(s) in `urls.txt` dominate the task stream**.

2) **Worker profile strategy is “per store *per slot*”** (`apps/worker/src/gloorbot_worker/slot_worker.py:147-148`).  
   This multiplies the number of “brand new” profiles, which (a) delays “seasoning” and (b) increases concurrent fresh sessions if multiple slots start on the same store.

3) **PARALLEL orchestrator assigns each worker to a distinct store and staggers worker launches**.  
   - Unique store assignment (`PARALLEL/orchestrator.py:513-521`)  
   - 5s stagger between worker launches (`PARALLEL/orchestrator.py:524`)  
   This is meaningfully different behavior from the Worker’s coordinator-driven task leasing.

4) **PARALLEL adds an explicit inter‑category delay; Worker does not**.  
   - PARALLEL sleep between categories (`PARALLEL/scraper.py:802-803`)  
   - Worker immediately leases the next task after each completion (no analogous sleep in `apps/worker/src/gloorbot_worker/slot_worker.py:211-320`).

5) **Build/packaging differences exist but look secondary** to the orchestration differences. The Worker installer build does *not* bundle Playwright browsers (workflow), while the local dev build script does (build.ps1).  
   - CI workflow says “do NOT bundle Chromium” (`.github/workflows/worker-build.yml:34-35`)  
   - Local build bundles `ms-playwright` and installs Chromium (`apps/worker/build.ps1:12-25`)  
   This can create “it works on my dev box” artifacts depending on how you built/ran the Worker.

---

## 1) What I investigated (high level)

- The “working” scraper: not just `PARALLEL/scraper.py`, but the actual runnable path in `PARALLEL/` (`start.bat` → `orchestrator.py` → `worker.py` → `scraper.py`).
- The Worker app call chain: `apps/worker/src/gloorbot_worker/__main__.py` → `gui.py` → `supervisor.py` → spawning slot workers → `slot_worker.py` → dynamic import of `PARALLEL/scraper.py`.
- Exact Playwright launch parameters and profile paths in both.
- Coordinator seeding + leasing behavior in `apps/coordinator`, because Worker behavior is driven by that scheduler.
- Git history around the Worker’s scraper changes (`git log -- apps/worker/src/gloorbot_worker/slot_worker.py`).
- Build pipelines (`.github/workflows/worker-build.yml`, `apps/worker/build.ps1`, `apps/worker/installer/worker.iss`).

---

## 2) Execution paths (what actually runs)

### 2.1 PARALLEL runner (what “works” in this repo)

Despite the name, **the runnable entrypoint is not `scraper.py` directly**. The PARALLEL README instructs:

- `start.bat` launches `python orchestrator.py --state WA,OR --max-workers 5` (`PARALLEL/README.md:25-30`, `PARALLEL/start.bat:28`)

Then:

1. `PARALLEL/orchestrator.py` launches multiple `PARALLEL/worker.py` subprocesses, each bound to a *specific store* (unique assignment) (`PARALLEL/orchestrator.py:513-521`).
2. `PARALLEL/worker.py` imports `PARALLEL/scraper.py` and monkeypatches `scraper.Actor` with a `MockActor`, then runs `asyncio.run(tracked_main())` (`PARALLEL/worker.py:96-170`).
3. `PARALLEL/scraper.py` is used as a library (warmup/session + category scraping) by those workers.

### 2.2 Worker application (what “gets blocked”)

Worker has two modes in one executable:

- Default: GUI mode (Tkinter)
- Child processes: “slot worker mode”

Relevant files:

- Entry: `apps/worker/src/gloorbot_worker/__main__.py:17-24`  
  If `--slot-worker` is present, it runs `slot_worker_main`; otherwise it runs GUI.
- GUI spawns supervisor loop: `apps/worker/src/gloorbot_worker/gui.py:76-103`
- Supervisor spawns slot processes: `apps/worker/src/gloorbot_worker/supervisor.py:79-112`  
  In frozen builds it spawns `sys.executable --slot-worker ...` (`apps/worker/src/gloorbot_worker/supervisor.py:85-93`).
- Slot worker dynamically loads the PARALLEL scraper: `apps/worker/src/gloorbot_worker/slot_worker.py:46-56`
- Slot worker then calls `parallel.warmup_session`, `parallel.set_store_context`, and `parallel.scrape_category_all_pages` (`apps/worker/src/gloorbot_worker/slot_worker.py:200-256`).

---

## 3) Browser launch config: “looks the same”… mostly

### 3.1 PARALLEL launch kwargs

In `PARALLEL/scraper.py`, launch uses **Chrome channel** and **headless=False** with a specific arg list:

```py
# PARALLEL/scraper.py:760-778 (excerpt)
launch_kwargs = {
    "headless": False,  # Must be False - Lowe's blocks headless
    "channel": "chrome",
    "viewport": {"width": 1440, "height": 900},
    "locale": "en-US",
    "timezone_id": "America/Los_Angeles",
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-infobars",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--memory-pressure-off",
    ]
}

context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
```

(`PARALLEL/scraper.py:760-784`)

### 3.2 Worker launch kwargs

Worker tries to match that config and uses system Chrome:

```py
# apps/worker/src/gloorbot_worker/slot_worker.py:147-176 (excerpt)
profile_dir = profiles_dir() / f"store-{lease.store_id}" / f"slot-{slot_id}"
...
launch_kwargs = {
    "headless": False,
    "viewport": {"width": 1440, "height": 900},
    "locale": "en-US",
    "timezone_id": "America/Los_Angeles",
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-infobars",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--memory-pressure-off",
    ],
}

context = await p.chromium.launch_persistent_context(str(profile_dir), channel="chrome", **launch_kwargs)
```

(`apps/worker/src/gloorbot_worker/slot_worker.py:147-190`)

### 3.3 Conclusion on launch options

The **explicit** kwargs are effectively aligned. That pushes suspicion away from “Chrome args mismatch” and toward:

- profile handling differences
- task pacing / navigation cadence differences
- coordinator/scheduler behavior differences

---

## 4) Profile handling: not equivalent between systems

### 4.1 Where profiles live

- PARALLEL uses a relative directory `.playwright-profiles/store-<store_id>` (`PARALLEL/scraper.py:757-758`).  
  When you run from the `PARALLEL/` folder, this becomes `PARALLEL/.playwright-profiles/store-<id>`.

- Worker uses `%LOCALAPPDATA%\\GloorbotWorker\\profiles\\...` (`apps/worker/src/gloorbot_worker/paths.py:7-22`) and adds a **slot** dimension:  
  `profiles/store-<id>/slot-<slot_id>` (`apps/worker/src/gloorbot_worker/slot_worker.py:147-148`)

### 4.2 Per-store vs per-store-per-slot is a big deal

PARALLEL’s design (as used in `scraper.py`) is one profile per store. Worker is one profile per store *per slot*.

Implications:

- If multiple slots start on the same store (see coordinator seeding), Worker creates **multiple fresh profiles** for that store concurrently.
- “Seasoning” now has to happen N times (once per slot per store), not once per store.

This aligns with the symptom “seasoned profiles work; fresh profiles get blocked”.

---

## 5) Task pacing & navigation cadence differences

### 5.1 PARALLEL adds a deliberate delay between categories

After each category scrape, PARALLEL sleeps:

```py
await asyncio.sleep(2.0 + random.random() * 2.55)  # 2.0-4.55 sec between categories
```

(`PARALLEL/scraper.py:802-803`)

### 5.2 Worker does not have an equivalent “think time”

Worker completes a lease, reports completion, and immediately requests another lease (`apps/worker/src/gloorbot_worker/slot_worker.py:211-276`), without an inter-lease delay.

Even if each category scrape has internal sleeps (it does), removing the inter‑category jitter is a meaningful change in rhythm/pattern.

---

## 6) Coordinator scheduling: the biggest non-obvious difference

This is the strongest “why would the same scraper code behave differently?” evidence I found.

### 6.1 Task seeding order is store-major (clustered by store)

Coordinator seeds tasks like this:

```py
for store in stores:
    for category_url in categories:
        db.add(Task(store_id=store["store_id"], category_url=category_url, ...))
```

(`apps/coordinator/coordinator_app/seed.py:63-78`)

This means Task IDs in the database are naturally grouped:

- all categories for store #1, then
- all categories for store #2, then
- etc.

### 6.2 Lease order prefers “oldest/never completed” then `id`

Leasing does:

```py
query = select(Task).where(base_filter)
if req.preferred_store_id:
    query = query.order_by((Task.store_id != req.preferred_store_id).asc())
query = query.order_by(Task.last_completed_at.asc().nullsfirst(), Task.id.asc()).limit(1)
```

(`apps/coordinator/coordinator_app/web.py:241-245`)

### 6.3 Combined implication: startup “store clustering”

At the start (fresh DB or largely incomplete tasks), `last_completed_at` is `NULL` for most tasks, so `id` becomes the dominant ordering. Because IDs are store-major, the system will hand out leases primarily for **the first store in the seed list**.

If you have multiple slots:

- Slot 0 leases the first task (store 0061).
- Slot 1 starts shortly after and leases the next available task (very likely still store 0061).
- etc.

Result: **multiple simultaneous sessions targeting the same store immediately**, each with fresh profile state. That is an orchestration difference from PARALLEL’s unique-store-per-worker model.

### 6.4 How PARALLEL avoids this

PARALLEL assigns workers to distinct stores:

```py
assigned_stores = {w.store_info['store_id'] for w in self.workers}
next_store = next((s for s in self.stores if s['store_id'] not in assigned_stores), None)
...
worker = WorkerProcess(worker_id, next_store, self.output_dir)
```

(`PARALLEL/orchestrator.py:513-520`)

And it staggers launches by 5 seconds (`PARALLEL/orchestrator.py:524`).

This is a fundamentally different “shape” of traffic at startup.

---

## 7) Build / packaging differences that can skew your comparisons

### 7.1 CI installer build does NOT bundle Playwright browsers

Workflow explicitly calls this out:

- “We do NOT bundle Chromium anymore” (`.github/workflows/worker-build.yml:34-35`)

And the pyinstaller invocation only adds `PARALLEL` as data (`.github/workflows/worker-build.yml:41-52`).

### 7.2 Local dev build script DOES bundle Chromium

Local build script:

- Sets `PLAYWRIGHT_BROWSERS_PATH=ms-playwright` (`apps/worker/build.ps1:12`)
- Installs Chromium into that folder (`apps/worker/build.ps1:13`)
- Bundles `ms-playwright` into the distribution (`apps/worker/build.ps1:24`)

So depending on how you “ran the worker on your dev machine”, you may have been comparing:

- worker build A (with `ms-playwright` bundled) vs
- worker build B (installer build without browsers bundled)

### 7.3 Installer installs into LocalAppData

The Inno Setup installer uses:

- `DefaultDirName={localappdata}\\GloorbotWorker` (`apps/worker/installer/worker.iss:9`)

So your exe and your app data directory are effectively the same root (because `app_data_dir()` is also `%LOCALAPPDATA%\\GloorbotWorker`) (`apps/worker/src/gloorbot_worker/paths.py:7-12`).

This is probably fine, but it’s worth knowing because it means upgrades/installs can potentially interact with existing data in that same folder (profiles/logs/config).

---

## 8) How the findings map to your observed symptom

Symptom: “Worker works after weeks; Worker fails on fresh machine or after deleting `%LOCALAPPDATA%\\GloorbotWorker\\profiles\\`.”

The codebase supports a straightforward explanation that doesn’t require “mystical PyInstaller differences”:

1. A “seasoned” profile is different from a fresh profile (cookies/state/history). This repo itself repeatedly treats persistent profiles as critical (e.g., `PARALLEL/scraper.py:124-145`, `PARALLEL/scraper.py:757-784`).
2. Worker creates many fresh profiles (per store *per slot*) and likely starts multiple slots that cluster on the same store due to coordinator ordering.
3. PARALLEL assigns unique stores per worker and adds extra pacing (sleep between categories), producing a more stable/less bursty startup behavior.

If all three are true, it is plausible that:

- PARALLEL appears “reliably working” because it (a) spreads load and (b) has already-seasoned store profiles in `PARALLEL/.playwright-profiles/`.
- Worker appears “instantly blocked” on fresh installs because it (a) starts with multiple fresh profiles and (b) concentrates on one store first due to coordinator ordering.

---

## 9) Suggested experiments (evidence-gathering, minimal changes)

These are designed to quickly validate/kill the top hypotheses without large refactors.

### 9.1 Verify whether PARALLEL truly works with *fresh* profiles

Goal: rule out “PARALLEL only works because its repo profiles are already seasoned”.

Experiment:

- Rename `PARALLEL/.playwright-profiles/` to `PARALLEL/.playwright-profiles.BAK/`
- Run PARALLEL with a single worker and a single store (to reduce confounders).

If PARALLEL now reproduces “fresh profile blocking”, then the Worker’s behavior is less mysterious: it’s the same underlying requirement for seasoned state, plus more aggressive orchestration.

### 9.2 Confirm “store clustering” in Worker at startup

Goal: see if multiple slots start on the same store (as predicted by seed + lease ordering).

Experiment:

- Start Worker with 2+ slots (let supervisor scale or force it).
- Inspect `...\\GloorbotWorker\\status\\slot_*.json` (written by slot workers, `apps/worker/src/gloorbot_worker/slot_worker.py:227-240`).
- Look at the first few `store_id` values per slot.

Expected if hypothesis is right: many slots show the same `store_id` early (likely the first store in `urls.txt`, which is `0061` in `PARALLEL/urls.txt:7`).

### 9.3 Run Worker with exactly one slot and watch fresh profile behavior

Goal: separate “fresh profile cannot pass challenge at all” from “multi-slot clustering creates the block”.

Experiment:

- Run only a single slot worker process (bypass supervisor scaling) and keep everything else identical.
- If 1 slot still gets blocked reliably, the root is more likely “fresh profile pass is failing” than “concurrency”.

### 9.4 Compare basic “browser identity” signals between PARALLEL and Worker

Goal: verify the browser context is truly identical (Chrome channel, UA, webdriver, etc.), not accidentally different.

Experiment (preferably temporary logging only):

- Capture:
  - `navigator.userAgent`
  - `navigator.webdriver`
  - timezone / locale
  - Chrome version from `browser.version()` (Playwright API)

Do this in both paths for the same machine and compare.

### 9.5 Inspect *names only* of cookies/state after warmup (no values)

Goal: determine whether the warmup is actually establishing the expected session state on fresh profiles.

Experiment:

- After `warmup_session()` (`PARALLEL/scraper.py:124-145`) and after `set_store_context()` (`PARALLEL/scraper.py:148-188`), dump cookie **names** for `lowes.com` from the context for:
  - PARALLEL run
  - Worker run

If cookie names differ materially on fresh profiles, then one of the flows isn’t actually completing the same “session establishment” steps.

### 9.6 Change only coordinator ordering (small controlled experiment)

Goal: test if store clustering is a major driver.

Experiment (smallest possible change, in a temporary branch):

- Interleave task insertion order (e.g., categories outer loop, stores inner loop) in `seed_tasks_from_parallel_urls`.
- Or change lease query to randomize across store_id when `last_completed_at` is NULL-heavy.

If Worker suddenly survives fresh profiles much more often, you have strong evidence the orchestration pattern is the trigger.

---

## 10) Open questions / unknowns

1. Have we conclusively tested PARALLEL on a truly fresh machine/profile set (no preexisting profiles anywhere)?  
   The repo currently contains existing profile folders under `PARALLEL/.playwright-profiles/` which could be “doing the real work”.

2. On the fresh machine where Worker blocks quickly: how many slots were running at the time?  
   If it was >1, coordinator clustering could be a primary trigger.

3. Are tasks in the coordinator DB fully reset between tests?  
   If tasks remain partially completed, the lease ordering changes, which could explain “it worked last week” vs “it blocks now”.

4. Are we comparing the same Worker build artifact in both places?  
   Local build (`apps/worker/build.ps1`) and CI build (`.github/workflows/worker-build.yml`) are materially different regarding Playwright browser bundling.

---

## Appendix A: Relevant git history (Worker slot_worker)

`git log -- apps/worker/src/gloorbot_worker/slot_worker.py` shows rapid iterations around stealth injection and “matching PARALLEL config”. Recent tags:

- `v0.2.1` “REVERT TO PROVEN: Remove ALL fingerprint injection” (commit `ae45f2a8`)
- `v0.2.0` “MAJOR OVERHAUL … comprehensive scraper hardening” (commit `589486ed`)
- `v0.1.8` “Match PARALLEL scraper Chrome config exactly” (commit `d88872fc`)
- `v0.1.7` “Fresh profile detection with extended … pre-warmup” (commit `552b27bb`)
- `v0.1.6` “Remove Chromium - Chrome is now required” (commit `6d3808f7`)
- `v0.1.5` “Add anti-detection stealth scripts” (commit `b26dca71`)

This history suggests the team already converged on “don’t overdo stealth; match the proven run”, which is consistent with the launch kwargs now being aligned.

