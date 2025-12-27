# Lowe’s URL Minimization — Methodology & Findings

You asked for **100% confidence** that a URL list is both:

1) **Complete** (exposes the whole catalog), and
2) **Minimal** (no redundant URLs).

On Lowe’s, those goals conflict unless we’re explicit about what “complete” means, because:
- the sitemap contains hundreds of thousands of `/pl/` URLs (many are refinements/filters),
- the Departments UI only links to a subset of those,
- and “minimal over products” is a set-cover problem that requires deep product enumeration to prove.

This repo now contains reproducible outputs for **structural minimality** and **measured redundancy**.

## Phase 1 — Full audit of your original list (browser, proved)

We ran a real-Chrome Playwright audit of the URLs in `LowesMap.txt`:
- Script: `audit_all_urls.py`
- Output: `url_audit_results.json` (+ `url_audit_results.jsonl`, `url_audit_run.log`)

Result:
- The 515 URLs collapse to **505 unique base category IDs** (exact duplicates exist).
- Canonical deduped list: `MINIMAL_URLS_FROM_AUDIT.txt`
- Exact duplicate groups are documented in `DUPLICATE_GROUPS_FROM_AUDIT.md`.

This proves: you can reduce **515 → 505** without losing any base-ID coverage present in the original list.

## Phase 2 — Departments UI discovery (browser, incomplete for catalog coverage)

We crawled from `https://www.lowes.com/c/Departments` and recursively visited `/c/` hubs:
- Script: `discover_department_urls.py`
- Outputs: `discovered/departments_raw.json`, `discovered/pl_candidates.txt`, `discovered/c_visited.txt`

Then we structurally minimized those candidates:
- Script: `minimize_department_urls.py`
- Outputs: `discovered/pl_minimal_structural.txt`, `discovered/pl_groups_by_category_id.json`

Result:
- Departments discovery produced **798** base category IDs.
- Sitemap base category universe is **3,597** base IDs, so Departments discovery alone cannot be used to claim “full catalog” coverage.

See `gap_analysis.json` and `GAP_ANALYSIS.md`.

## Phase 3 — Sitemap structural minimal set (proved)

Using the existing `sitemap_comparison.json` (from `fetch_lowes_sitemaps.py`), we reconstructed the full sitemap `/pl/` universe and collapsed it by base category ID:
- Script: `build_sitemap_minimal_urls.py`
- Outputs:
  - `master_sitemap_pl_list.txt` (497,492 `/pl/` URLs)
  - `sitemap_pl_groups_by_base_id.json`
  - `sitemap_minimal_structural_urls.txt` (3,597 canonical URLs)
  - `sitemap_duplicate_groups_structural.md`

We then set:
- `MINIMAL_URLS.txt` = **the 3,597-url sitemap structural minimal list**

This proves: for the sitemap’s category universe, **one URL per base category ID** is structurally minimal (everything else is a refinement/variant of an already-covered base ID).

## Phase 4 — Targeted “no unrefined /<id> URL” checks (partial)

Some discovered base IDs had no clean unrefined URL. We started auditing those variants:
- Inputs: `discovered/no_unrefined_urls.txt`, `discovered/no_unrefined_groups.json`
- Partial audit output: `discovered/no_unrefined_audit.json`
- Conservative reduction: `discovered/no_unrefined_recommended_keep.txt` and `discovered/no_unrefined_reduction_report.md`

Because the audit is partial, the reduction remains conservative (keeps most variants).

## Key conclusion (honest)

- We can be **100% confident** about *structural* deduplication by base category ID.
- We **cannot** honestly claim “absolute minimal over products” without enumerating product membership across categories (set-cover), which is far beyond first-page sampling and would require substantial scraping.

If your operational definition of “complete” is “covers every category base ID Lowe’s publishes in their sitemaps”, then `MINIMAL_URLS.txt` is the correct complete + structurally minimal list.
