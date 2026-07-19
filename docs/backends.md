# Backends

## gee (default)

All imagery access, compositing and the final full-image classification run server-side
in Google Earth Engine. Only training pixels are pulled locally (for scikit-learn
cross-validation and model comparison); the winning model is retrained natively with
`ee.Classifier.smileRandomForest` / `smileGradientTreeBoost` / `libsvm` and applied to
the full feature stack in GEE, then exported to Drive or an asset.

Requirements: an Earth Engine account and a GEE-enabled Google Cloud project
(`project.gee_project_id`). Authenticate once with `lulc auth`, or use
`lulc auth --service-account key.json` for non-interactive environments.

## local (planned, M2)

Classify user-supplied GeoTIFF stacks with rasterio + scikit-learn — no Earth Engine
account needed. Intended for orgs that already produce their own composites or work
with drone/aerial imagery. Selecting `backend: local` currently raises
`NotImplementedError`.

## stac (planned, M3)

Imagery from STAC catalogs (Microsoft Planetary Computer, Element 84 Earth Search) as a
fully GEE-free acquisition path.
