# Example: forest_monitoring

A 4-class (Forest / Agriculture / Water / Built-up) Sentinel-2-era workflow over a demo
AOI (a 15 km buffer on the southwestern slopes of Mount Kenya near Naro Moru, picked
because it packs forest, farmland, water and towns into one scene).

The included training polygons (6 per class) were sampled from homogeneous patches of
**ESA WorldCover v200 (2021)**, so the demo classifies against real reference labels.
Running `lulc classify -c lulc.yaml --year 2022` end-to-end yields ~95% overall
accuracy (polygon-grouped CV, RF). For real projects, draw 15-30 polygons per class
with `lulc labels template` — more polygons means more informative folds.

## Run it

```bash
cd examples/forest_monitoring
# Point project.gee_project_id in lulc.yaml at your own GEE Cloud project first.

lulc auth
lulc validate -c lulc.yaml
lulc check -c lulc.yaml
lulc features -c lulc.yaml --year 2022     # inspect the full candidate band list
lulc analyze -c lulc.yaml --year 2022      # correlation / VIF / importance reports
lulc classify -c lulc.yaml --year 2022     # CV -> best model -> classify -> Drive export
```

After `lulc analyze`, optionally write `selected_features_2022.json`
(`{"features": ["SAVI", "NDMI", ...]}`) next to `lulc.yaml` and re-run `lulc classify`
to use the pruned set.

## Collect better training data

```bash
lulc labels template -c lulc.yaml --year 2022
```

Paste the generated `collector_2022.js` into the [GEE Code Editor](https://code.earthengine.google.com/),
draw one FeatureCollection per class (`Forest`, `Agriculture`, `Water`, `Builtup`), then
export and save as `training/training_2022.geojson`.
