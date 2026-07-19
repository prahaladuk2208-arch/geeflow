# Config reference (`lulc.yaml`)

Every section except `aoi` and `classes` has working defaults. Relative paths resolve
against the config file's directory. String values may reference environment variables
as `${VAR_NAME}`.

## project

| key | default | notes |
|-----|---------|-------|
| `name` | `my-lulc-project` | used in reports |
| `gee_project_id` | none | Google Cloud project for `ee.Initialize` |
| `backend` | `gee` | `local` (rasterio/sklearn) is planned |

## aoi — exactly one of

```yaml
aoi:
  center_buffer: { lat: ..., lon: ..., radius_m: ... }
  # geojson: path/to/aoi.geojson          (Feature, FeatureCollection or geometry)
  # ee_asset: projects/<proj>/assets/aoi  (FeatureCollection asset)
```

## time_points

List of years (1972-2100). Any year works — the sensor era is resolved automatically.

## sensor_eras

Defaults: `mss` (≤1983, 60 m, ±2 yr window, merged sensors, always expanded),
`tm` (≤2013, 30 m, ±1 yr), `s2` (>2013, 10 m). Override to change scales, windows, or
pin explicit sensor keys:

```yaml
sensor_eras:
  - { name: tm, max_year: 2013, scale_m: 30, search_window_yr: 1 }
  - { name: s2, max_year: 9999, scale_m: 10, sensors: [sentinel2_sr] }
```

Sensor keys: `landsat_mss_l1..l5`, `landsat5_t1_sr`, `landsat7_t1_sr`, `landsat8_sr`,
`landsat9_sr`, `sentinel2_sr`.

## seasons

```yaml
seasons:
  - { name: dry, months: [1, 3] }     # inclusive month range
  - { name: wet, months: [11, 2] }    # start > end wraps into the next year
```

The first season (or `features.seasonal.reference_season`) is the reference: its
composite is the base of the feature stack, and cross-season features are computed
against it. One season = no cross-season features.

## composite

| key | default | notes |
|-----|---------|-------|
| `reducer` | `median` | or `mean` |
| `min_scenes` | 3 | below this the fallback ladder kicks in (backup sensor, then window expansion) |

## features

```yaml
features:
  indices: [NDVI, SAVI, EVI, NDMI, NBR, BlueGreenNIR, GreenRed]
  texture: { enabled: true, band: NIR, metrics: [entropy, contrast], window: 3, exclude_eras: [mss] }
  seasonal:
    deltas: true          # delta_<X>_<season> = X(season) - X(reference)
    ratios: true          # <X>_ratio_<season> = X(reference) / X(season)
    season_values: true   # <X>_<season>
    # delta_indices / ratio_indices / value_indices: restrict to a subset (default: all)
```

Known indices: `NDVI SAVI EVI NDMI NBR BlueGreenNIR GreenRed NDRE CIre NDWI NDBI`.
An index is only computed when its required bands exist in the era (MSS lacks
Blue/SWIR, so e.g. EVI/NDMI drop out automatically).

## classes

```yaml
classes:
  0: Forest
  1: Agriculture
  2: Water
```

Any number of integer-coded classes.

## training

| key | default | notes |
|-----|---------|-------|
| `path` | `training/training_{year}.geojson` | `{year}` substituted |
| `ee_asset` | none | load an EE FeatureCollection asset instead of a file |
| `class_property` | `class` | integer class code property |
| `group_property` | `polygon_id` | grouping key for spatial CV (auto-assigned) |
| `min_polygons_per_class` | 5 | warning threshold |

## classifier

| key | default |
|-----|---------|
| `candidates` | `[RF, GBT, SVM]` |
| `rf` | `{ trees: 800, bag_fraction: 0.9, seed: 42 }` |
| `gbt` | `{ trees: 500, seed: 42 }` |
| `svm` | `{ kernel: RBF, cost: 10, gamma: 0.1 }` |
| `cv` | `{ folds: 5, seed: 42 }` |
| `feature_selection` | `selected_features_{year}.json` — used if the file exists |

## analysis

`correlation_threshold` (0.5) and `vif_threshold` (10) control what `lulc analyze`
flags. Analysis only reports; pruning is always the user's decision.

## postprocess

```yaml
postprocess:
  majority_filter: { enabled: true, kernel: 3, iterations: 1 }
  min_mapping_unit_ha: 0.5    # optional; small patches replaced by neighborhood mode
```

## export

| key | default | notes |
|-----|---------|-------|
| `target` | `drive` | or `asset` (requires `asset_root`) |
| `folder` | `LULC_Outputs` | Drive folder |
| `prefix` | `classified` | file/asset name prefix |
| `crs` | `EPSG:4326` | |
| `scale_m` | native era scale | override to resample |
| `max_pixels` | `1e10` | |

## output_dir

Default `outputs` (figures/ and tables/ are created inside it).
