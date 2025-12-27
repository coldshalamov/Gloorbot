# Duplicate URL Groups (What We Can Prove)

This project has **three different “duplicate” concepts**:

1) **Exact duplicates within the 515 URLs** (same base category ID → same pool)
2) **Structural duplicates within the sitemap** (same base category ID → refinements/filters)
3) **Potential product-level duplicates across different base IDs** (hard; requires enumerating product IDs across pages)

This file only claims what we can prove with the current data.

## A) Exact duplicates in the original 515-url list (proved)

From the full browser audit (`url_audit_results.json`), these base IDs appeared multiple times in `LowesMap.txt`:

- Base ID `4294713162` (5 URLs)
- Base ID `4294737158` (2 URLs)
- Base ID `4294737274` (6 URLs)

These are summarized in `DUPLICATE_GROUPS_FROM_AUDIT.md`. The deduped list that keeps one canonical URL per base ID is `MINIMAL_URLS_FROM_AUDIT.txt` (505 URLs).

## B) Structural duplicates in the sitemap (proved)

The sitemap-derived universe contains **497,492** `/pl/` URLs that collapse to **3,597** base category IDs.

- Structural “duplicate groups” (base IDs with >1 URL) are enumerated in `sitemap_duplicate_groups_structural.md`.
- The structurally minimal canonical list (one URL per base ID) is `MINIMAL_URLS.txt` (copied from `sitemap_minimal_structural_urls.txt`).

## C) Department discovery duplicates (partially proved)

The Departments UI crawl (`discover_department_urls.py`) produced:

- `discovered/pl_candidates.txt`: all discovered candidates
- `discovered/pl_groups_by_category_id.json`: grouping + canonical selections
- `discovered/pl_minimal_structural.txt`: conservative structural minimization (1068 URLs; 798 base IDs)

Some base IDs had no unrefined `/.../<id>` URL, so we conservatively kept all variants for those IDs. We started a targeted audit of those “no-unrefined” variants in:

- `discovered/no_unrefined_audit.json` (partial)
- `discovered/no_unrefined_reduction.json` / `discovered/no_unrefined_recommended_keep.txt` (conservative; incomplete audits keep all)

## What is NOT proved here

“Vanities by size” vs “Vanities by brand” style duplication across **different base IDs** is a true product-level set-cover problem; proving minimality requires much deeper, per-product enumeration than first-page samples.
