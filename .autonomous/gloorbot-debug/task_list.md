# gloorbot-debug

Goal: Determine why Render deployments (`gloorbot-coordinator`, `gloorbot`) and the local scraper pipeline produce incorrect deal prices and unexpected Chrome window counts.

## Tasks

- [ ] Identify Render service IDs for `gloorbot-coordinator` and `gloorbot`
- [ ] Pull latest deploy status + build logs for both services
- [ ] Pull recent runtime logs for both services (last ~6 hours)
- [ ] Map data flow: local scraper → coordinator → gloorbot API → DB → UI
- [ ] Find where `price` becomes `percent` (e.g., `$4.00` from `4%`)
- [ ] Reproduce locally with a captured HTML example or unit test
- [ ] Implement minimal fix with validation (don’t break other fields)
- [ ] Verify fix end-to-end (local + Render logs show success)
