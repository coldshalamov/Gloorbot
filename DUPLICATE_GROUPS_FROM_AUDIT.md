# Duplicate groups from audit

## Exact duplicates (same category ID)
- ID `4294713162` (5 URLs)
  - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/clear/4294713162-4294701074`
  - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/semi-solid/4294713162-4294646621`
  - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/semi-transparent/4294713162-4294702376`
  - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/solid/4294713162-4294702377`
  - `https://www.lowes.com/pl/exterior-wood-coatings/exterior-stains/transparent/4294713162-4294867931`
- ID `4294737158` (2 URLs)
  - `https://www.lowes.com/pl/bathroom-safety/bathroom-safety-accessories/4294737158`
  - `https://www.lowes.com/pl/bathroom-safety/bathroom-safety-accessories/toilet-seat-riser/4294737158-910305200700`
- ID `4294737274` (6 URLs)
  - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/alcove/4294737274-1895254902`
  - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/clawfoot/4294737274-714937190`
  - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/corner/4294737274-4294883811`
  - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/drop-in/4294737274-3577694822`
  - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/freestanding/4294737274-1040479095`
  - `https://www.lowes.com/pl/bathtubs-whirlpool-tubs/bathtubs/walk-in/4294737274-4294964535`

## Candidate duplicates (identical first-page SKU samples across different IDs)
- These are *candidates only* (false positives possible): identical first-page samples do not prove full-set equality.
- Sample `1005187,1036991,1072945,1090933,1099657...` (3 URLs, IDs: 1820112634192, 4294395587, 4294612471)
  - `https://www.lowes.com/pl/Appliance-power-cords-Appliance-parts-accessories/4294612471`
  - `https://www.lowes.com/pl/Fireworks-Outdoor-recreation/1820112634192`
  - `https://www.lowes.com/pl/Radiator-covers-Heating-cooling/4294395587`
- Sample `5001651819,5014571143,5013685023,5015305059,1000615427...` (2 URLs, IDs: 4294641547, 4294644700)
  - `https://www.lowes.com/pl/Spark-plugs-Automotive/4294641547`
  - `https://www.lowes.com/pl/automotive/4294644700`
