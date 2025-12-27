# Gap Analysis

This compares different URL sources against the sitemap-derived base category universe.

## Counts

- sitemap_min_urls: 3597
- sitemap_base_ids: 3597
- discovered_min_urls: 1068
- discovered_base_ids: 798
- lowesmap_urls: 569
- lowesmap_base_ids: 505
- audit_min_urls: 505
- audit_min_base_ids: 505

## Base ID Overlap

- discovered_vs_sitemap: 786
- missing_from_discovered_vs_sitemap: 2811
- extra_in_discovered_vs_sitemap: 12
- lowesmap_vs_sitemap: 463
- missing_from_lowesmap_vs_sitemap: 3134

## Interpretation

- The sitemap-derived set is the only one that approaches catalog-scale coverage (thousands of base category IDs).
- The Departments UI discovery covers a *subset* of sitemap base IDs; it is useful for navigation analysis, but it is not sufficient to claim full catalog coverage.
- The original 515-url LowesMap set is also a small subset of the sitemap base IDs; reducing it to 505 only removes exact duplicates and does not improve coverage.

## Notes

- This is *structural* coverage at the **base category id** level; it does not prove a mathematical minimal set-cover over products.
