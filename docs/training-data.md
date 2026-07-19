# Training data

## Formats

**M1 (current):**

- **GeoJSON** files (Point / Polygon / MultiPolygon features) with an integer class
  property (`training.class_property`, default `class`).
- **Earth Engine FeatureCollection assets** — set `training.ee_asset`. This is the
  easiest way for a partner organization to share labels: they share the asset with
  your account, you point the config at it.

**Planned (M2):** shapefile, KML/KMZ, GPX and CSV field/GPS points, plus training
labels sampled automatically from public LULC products (Dynamic World, ESA WorldCover,
Hansen GFC) with agreement/consensus logic.

## Spatial cross-validation grouping

Every training feature gets a `polygon_id` (config: `training.group_property`).
Cross-validation uses `StratifiedGroupKFold` grouped by that id, so all pixels sampled
from one polygon stay in the same fold. Without this, neighboring pixels from a single
polygon end up in both training and validation folds and accuracy is overestimated.

This is why you should draw **many small polygons** rather than a few large ones:
more groups = more informative folds.

## Collecting polygons

`lulc labels template --year Y` generates a GEE Code Editor script bound to your AOI,
sensor era, seasons and class scheme, with a live pixel-info panel (click the map to see
NDVI/NDMI/delta values while deciding a label). Draw one FeatureCollection per class,
uncomment the export block, and save the GeoJSON to your `training.path`.

Guidelines:

- 15-30 polygons per class, spread across the AOI.
- Keep polygons small and homogeneous (avoid mixed edges).
- Label what the imagery shows in that year, not what a map says today.

## Sharing between organizations

Send your collaborator the `lulc.yaml` and the `training/` folder (or share an EE
asset). They run the identical pipeline — same sensors, features, CV scheme and
classifier settings — from the same config.
