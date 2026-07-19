# Changelog

## 0.1.0 (unreleased)

Initial release (M1):

- Config-driven LULC pipeline on Google Earth Engine: YAML project config validated with pydantic.
- Multi-era sensor support (Landsat MSS / TM / ETM+ / OLI, Sentinel-2) with automatic
  sensor selection per year, cloud masking, and band harmonization to standard names.
- Seasonal median composites with scene-count fallback ladder (backup sensor, window expansion).
- Config-driven spectral index registry, GLCM texture, and multi-season delta/ratio features.
- Training data from GeoJSON files or Earth Engine FeatureCollection assets, with
  per-polygon grouping for spatially safe cross-validation.
- Feature analysis (correlation matrix, VIF, preliminary RF importance) — report-only,
  never auto-prunes.
- Classifier comparison (RF / GBT / SVM) via polygon-grouped StratifiedGroupKFold CV,
  McNemar's test, native GEE retrain of the best model, majority-filter postprocessing,
  Drive/Asset export, JSON accuracy report.
- `lulc` CLI: init, auth, validate, check, composite, features, labels, analyze, classify, run.
- GEE Code Editor training-polygon collector script generated from config (Jinja2 template).
