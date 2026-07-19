# Quickstart

## Install

```bash
pip install lulc-engine        # or: pip install -e .[dev] from a clone
```

## 1. Scaffold a project

```bash
mkdir my-project && cd my-project
lulc init --template forest    # or --template basic (binary classes)
```

Edit `lulc.yaml`: set your AOI, `project.gee_project_id` (a Google Cloud project with
Earth Engine enabled), your classes, seasons and `time_points`.

## 2. Authenticate and sanity-check

```bash
lulc auth                      # one-time interactive Earth Engine login
lulc validate -c lulc.yaml     # config check + resolved sensor/era plan per year
lulc check -c lulc.yaml        # scene availability per year/season/sensor
```

## 3. Collect training data

```bash
lulc labels template -c lulc.yaml --year 2022
```

Paste the generated `collector_2022.js` into the [GEE Code Editor](https://code.earthengine.google.com/).
Draw one FeatureCollection of polygons per class (the script header names them), export,
and save the GeoJSON to the path in `training.path` — or import any GeoJSON you already have:

```bash
lulc labels import -c lulc.yaml --year 2022 -f my_polygons.geojson
```

Partner organizations can instead share an Earth Engine asset; set `training.ee_asset`.

## 4. Analyze features, then classify

```bash
lulc analyze -c lulc.yaml --year 2022
```

This computes **all** candidate features and writes a correlation heatmap, VIF table and
preliminary RF importance to `outputs/`. It never prunes automatically. Review the
reports, then (optionally) write `selected_features_2022.json`:

```json
{"features": ["SAVI", "NDMI", "delta_NDVI_wet", "GLCM_entropy"]}
```

```bash
lulc classify -c lulc.yaml --year 2022
```

This cross-validates RF/GBT/SVM with polygon-grouped folds, reports OA/Kappa/per-class
F1 and McNemar's test, retrains the winner natively in Earth Engine, applies the
majority filter, starts the export, and writes `classification_report_2022.json`.

## 5. All years at once

```bash
lulc run -c lulc.yaml
```
