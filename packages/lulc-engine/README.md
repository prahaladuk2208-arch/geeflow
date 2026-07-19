# lulc-engine

**Config-driven land-use / land-cover (LULC) classification workflows on Google Earth Engine.**

`lulc-engine` turns an LULC classification project into a single YAML file plus a folder of
training data. One organization can send a config to another and reproduce the exact same
workflow — sensors, composites, features, classifiers and all.

```
pip install lulc-engine
lulc init --template forest
lulc classify -c lulc.yaml --year 2022
```

## What it does

- **Auto-mosaic / composite** — picks the right sensor for any year (Landsat MSS → TM/ETM+ →
  OLI, Sentinel-2), cloud-masks, harmonizes band names across sensor eras, and builds
  seasonal median composites with automatic fallbacks when scenes are scarce (backup
  sensor, ± year window expansion).
- **Feature engineering** — a config-driven registry of spectral indices (NDVI, SAVI, EVI,
  NDMI, NBR, …), GLCM texture, and multi-season delta/ratio phenology features. All
  candidate features are computed; nothing is pruned automatically.
- **Bring your own training data** — GeoJSON polygons/points or an Earth Engine
  FeatureCollection asset shared by a partner organization. Every feature gets a
  `polygon_id` so cross-validation is grouped spatially (no leakage between folds).
- **Honest model selection** — RF, GBT and SVM compared with polygon-grouped
  StratifiedGroupKFold CV (overall accuracy, Kappa, per-class F1), McNemar's test between
  the top two, then the winner is retrained natively in Earth Engine and applied to the
  full image.
- **Feature analysis, not feature guessing** — `lulc analyze` writes a correlation
  heatmap, VIF table and preliminary RF importances. *You* decide what to prune, in a
  `selected_features_{year}.json` file.
- **Shareable by design** — the whole project is one `lulc.yaml`. Send it (plus training
  data) to a collaborator and they run the same pipeline.

## Quickstart

```bash
pip install lulc-engine
lulc init --template forest        # scaffolds lulc.yaml + training/ + outputs/
lulc auth                          # authenticate with Google Earth Engine
lulc validate -c lulc.yaml         # check the config, print the resolved run plan
lulc check -c lulc.yaml            # scene availability per year/season
lulc labels template -c lulc.yaml --year 2022   # GEE Code Editor script for drawing polygons
# ... draw + export training polygons, save to training/training_2022.geojson ...
lulc analyze -c lulc.yaml --year 2022           # correlation / VIF / importance reports
lulc classify -c lulc.yaml --year 2022          # CV -> best model -> classify -> export
```

Or from Python:

```python
from lulc_engine import load_config, Pipeline

cfg = load_config("lulc.yaml")
pipe = Pipeline(cfg)
stack = pipe.build_features(2022)      # ee.Image feature stack
result = pipe.classify(2022)           # CV + train + classify + export
```

## The config

```yaml
project:
  name: my-lulc-project
  gee_project_id: my-gee-project

aoi:
  center_buffer: { lat: 0.0, lon: 35.0, radius_m: 15000 }
  # or: geojson: aoi.geojson
  # or: ee_asset: projects/my-gee-project/assets/aoi

time_points: [2019, 2022, 2024]

seasons:
  - { name: dry, months: [1, 3] }
  - { name: wet, months: [10, 12] }

classes:
  0: Forest
  1: Agriculture
  2: Water
  3: Built-up

features:
  indices: [NDVI, SAVI, EVI, NDMI, NBR]
  texture: { enabled: true, band: NIR }
  seasonal: { deltas: true, ratios: true }

training:
  path: training/training_{year}.geojson
```

Everything has sensible defaults — see [docs/config-reference.md](docs/config-reference.md)
for the full schema. Sensor eras, band maps, classifier hyperparameters and analysis
thresholds are all overridable.

## Examples

- [`examples/forest_monitoring`](examples/forest_monitoring) — 4-class Sentinel-2-era
  workflow with demo training polygons.
- [`examples/historical_landsat`](examples/historical_landsat) — binary classification
  across Landsat TM and MSS eras, showing automatic sensor switching back to the 1970s.

## Requirements

- Python ≥ 3.10
- A Google Earth Engine account and Cloud project ([sign up](https://earthengine.google.com/))

## Roadmap

- **M2** — shapefile/KML/GPX/CSV training import, training labels sampled from public LULC
  products (Dynamic World, ESA WorldCover, Hansen GFC) with consensus logic, satellite
  embedding features, local GeoTIFF backend (rasterio + scikit-learn).
- **M3** — OpenStreetMap land-use ingest, STAC imagery backend (Planetary Computer /
  Earth Search), change-detection helpers.

## License

MIT
