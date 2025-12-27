# Duplicate URL groups

1. **ID 4294737158 – Bathroom safety accessories**
   - `https://www.lowes.com/pl/bathroom-safety/bathroom-safety-accessories/4294737158`
   - `https://www.lowes.com/pl/bathroom-safety/bathroom-safety-accessories/toilet-seat-riser/4294737158-910305200700`
   - Why it matters: the latter link is just a filter for toilet seat risers but resolves to the same category ID as the broader bathroom safety accessories bucket. Keeping only the parent URL avoids needless duplication.

2. **ID 4294737274 – Bathtubs (alcove, clawfoot, corner, drop-in, freestanding, walk-in)**
   - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/alcove/4294737274`
   - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/clawfoot/4294737274`
   - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/corner/4294737274`
   - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/drop-in/4294737274`
   - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/freestanding/4294737274`
   - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/walk-in/4294737274`
   - Why it matters: all six URLs share the same internal category ID, meaning the same product pool is reachable via multiple style filters. Keep just the general `/bathtubs` parent entry when deduplicating.

3. **ID 4294713162 – Exterior stains (clear, semi-solid, semi-transparent, solid, transparent)**
   - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/clear/4294713162`
   - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/semi-solid/4294713162`
   - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/semi-transparent/4294713162`
   - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/solid/4294713162`
   - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/transparent/4294713162`
   - Why it matters: the filters are just opacity/finish variants of the same category ID. One canonical `/exterior-wood-coatings/exterior-stains` URL covers the shared product set.

These groups are the only exact ID duplicates found in `url_dedupe_analysis.json`. During sampling we will confirm whether other filters redirect centrally or need separate tracking.
