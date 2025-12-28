# Deep Investigation: Why Does The Scraper Get Blocked?

## The Situation

We have a web scraper that monitors Lowe's hardware stores for deals. There are two ways to run it:

1. **The "PARALLEL" scraper** - A standalone Python script in the `PARALLEL/` folder that runs directly with `python scraper.py`. This one WORKS. It successfully scrapes Lowe's without getting blocked by their anti-bot system (Akamai).

2. **The "Worker" application** - A packaged Windows executable built with PyInstaller, distributed as an installer. This one gets BLOCKED almost immediately when run on a fresh computer.

The strange part is that the Worker application actually imports and uses the exact same scraping code from `PARALLEL/scraper.py`. It dynamically loads that module at runtime. So theoretically, it should behave identically. But it doesn't.

## The Mystery

When I run the Worker on my development machine (where I've been testing for weeks), it works fine. When I download the same installer on my home computer (or any fresh machine), it gets blocked by Akamai within seconds of trying to scrape a category page.

Even stranger: if I delete the browser profile folder on my dev machine (`%LOCALAPPDATA%\GloorbotWorker\profiles\`), then run the Worker again, it ALSO gets blocked. This strongly suggests the issue is related to browser profile state - a "seasoned" profile with history/cookies works, a fresh one doesn't.

But the PARALLEL scraper works even with fresh profiles when run directly. So what's different?

## What You Should Do

I want you to spend time - as much as you need - thoroughly investigating this codebase to understand what could possibly be different between:
- Running `python PARALLEL/scraper.py` directly
- Running the packaged `GloorbotWorker.exe`

Don't rush. Don't make assumptions. Read the code carefully. Follow the execution paths. Compare everything. Look at the git history to see what changed and when. Check for subtle differences that might seem unimportant but could matter to an anti-bot system.

## Some Context and Hints

The `PARALLEL/scraper.py` file has a header comment that documents what was learned through trial and error:

```
PROVEN WORKING APPROACH:
✅ Chrome channel (NOT Chromium)
✅ Persistent browser profiles
✅ Homepage warmup with human behavior
✅ NO playwright-stealth (red flag!)
✅ NO fingerprint injection (makes it worse!)
```

This is important. Early attempts to add "stealth" features (like hiding `navigator.webdriver` or spoofing browser plugins) actually made detection WORSE. The anti-bot systems are sophisticated enough to detect the inconsistencies these modifications create.

The worker code went through many iterations tonight trying to fix this. Check the git history - you'll see commits like:
- Adding stealth injection (bad idea)
- Removing Chromium fallback
- Matching Chrome launch args
- Adding extended warmup for fresh profiles
- Reverting stealth injection

None of these fully solved the problem.

## Key Areas to Explore

I'm not going to tell you exactly where to look because I don't know. But here are some vague directions:

**The browser launch process** - How is Playwright launching Chrome? Are there any subtle differences in how `slot_worker.py` creates the browser context versus how `PARALLEL/scraper.py` does it? Check every parameter. Check the order of operations.

**The profile handling** - Profiles are stored in different locations. Does this matter? What files exist in a working profile that don't exist in a fresh one? Could we "seed" a profile somehow?

**The PyInstaller packaging** - When the app runs from a PyInstaller bundle, things are different. The working directory is different. Environment variables might be different. The way modules are loaded is different. Does any of this affect how Playwright behaves?

**The dynamic module loading** - `slot_worker.py` uses `importlib` to dynamically load `PARALLEL/scraper.py`. Is this loading correctly? Is the loaded module actually the same as running it directly?

**The timing and flow** - Maybe something about the order of operations is different. Maybe there's a race condition. Maybe something happens too fast or too slow.

**The build process** - Check `.github/workflows/worker-build.yml`. Is the GitHub Actions build doing something that affects the final executable? Are the right dependencies included?

**Historical context** - Use git log, git blame, git diff to understand the history. Was there ever a version of the Worker that worked on fresh installs? If so, what changed?

## Your Output

Create a file called `investigation_findings.md` in the repo root. Write your findings there as you discover them. Be verbose. Document your thought process. Include code snippets and line numbers when relevant.

Structure it however makes sense to you, but include:
- What you investigated
- What you found
- What you think it means
- Questions that came up
- Theories about the root cause
- Suggested experiments or next steps

## Important Rules

1. **Do not make code changes** unless you have extremely high confidence they will help and are minimal. This is an investigation, not a fix attempt.

2. **Be thorough over fast**. I'm going to sleep. Take your time.

3. **Log everything**. Even if a finding seems unimportant, write it down. The answer might be in a combination of small things.

4. **Think like an anti-bot system**. What would YOU look for if you were trying to detect automation? What signals differentiate a real user from a script?

5. **Cross-reference constantly**. Every time you find something in one file, check if the equivalent exists in the other relevant files.

## Files to Start With

- `PARALLEL/scraper.py` - The working scraper
- `apps/worker/src/gloorbot_worker/slot_worker.py` - The worker's scraping logic
- `apps/worker/src/gloorbot_worker/paths.py` - Where profiles are stored
- `apps/worker/src/gloorbot_worker/__main__.py` - Entry point
- `apps/worker/src/gloorbot_worker/gui.py` - GUI launcher
- `.github/workflows/worker-build.yml` - Build process

But don't limit yourself to these. Explore anywhere that seems relevant.

## Final Thoughts

Somewhere in this codebase is the answer. The same scraping code works in one context and fails in another. The difference has to be environmental, configurational, or in the setup code that runs before the scraping starts.

Find it.
