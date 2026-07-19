# Example: historical_landsat

Binary (Vegetated / Non-Vegetated) classification reaching back to the 1970s, showing
how lulc-engine switches sensor eras automatically:

| year | era | sensor | scale |
|------|-----|--------|-------|
| 1978 | mss | Landsat MSS 1-3 (merged, ±2 yr window, TOA) | 60 m |
| 1995 | tm  | Landsat 5 TM | 30 m |
| 2010 | tm  | Landsat 5 + 7 fallback | 30 m |

In the MSS era only Green/Red/NIR bands exist, so the index registry automatically
reduces the feature set to what is computable (NDVI, SAVI, GreenRed) — nothing to
configure per era.

## Run it

```bash
cd examples/historical_landsat
# Point project.gee_project_id in lulc.yaml at your own GEE Cloud project first.

lulc validate -c lulc.yaml     # see the resolved era/sensor plan per year
lulc check -c lulc.yaml        # MSS-era scene counts are the interesting part
lulc labels template -c lulc.yaml --year 1978   # draw polygons on the 1978 composite
# save the export as training/training_1978.geojson, then:
lulc classify -c lulc.yaml --year 1978
```

No demo training data is bundled here — historical labeling really has to be drawn by a
human against the composite (that is what the generated collector script is for).
