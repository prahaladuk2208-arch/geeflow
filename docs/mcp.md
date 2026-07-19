# The geeflow MCP server

`geeflow-mcp` exposes Google Earth Engine workflows as fully-typed MCP tools, so AI
assistants (Claude Code, Claude Desktop, any MCP client) can search data, build
composites, inspect them visually and run classifications — while everything stays
reproducible.

## Setup

```bash
pip install "geeflow @ git+https://github.com/prahaladuk2208-arch/geeflow#subdirectory=packages/geeflow"
claude mcp add geeflow -- geeflow-mcp
```

Authenticate Earth Engine once on the machine (`earthengine authenticate`, or use a
service-account key). The assistant then starts every session with `gee_init`.

## Core tools

| tool | purpose |
|------|---------|
| `gee_init` | initialize Earth Engine (project id, optional service-account key) |
| `catalog_search` | keyword search over the GEE data catalog |
| `dataset_info` | metadata for an exact dataset id |
| `scene_availability` | scene counts per sensor over a region + date range |
| `build_composite` | cloud-masked, harmonized composite for a year/month window (auto sensor selection, fallback ladder); returns a `composite_id` |
| `compute_indices` | add NDVI/SAVI/EVI/NDMI/NBR/NDWI/NDBI/red-edge bands |
| `thumbnail` | PNG preview URL (true color, false color, or single-band with palette) |
| `region_stats` | per-band mean/median/minMax/stdDev over the region |
| `export_composite` | export to Google Drive or an EE asset |
| `export_tasks` | recent export task states |
| `sample_polygons` | auto-generate labeled training polygons from a categorical product (default ESA WorldCover) |
| `execute_code` | escape hatch: run arbitrary Earth Engine Python for anything the typed tools don't cover |

## LULC tools (registered when lulc-engine is installed)

| tool | purpose |
|------|---------|
| `lulc_validate` | validate a `lulc.yaml`, return the resolved year/era/sensor run plan |
| `lulc_check` | scene availability for every configured year/season |
| `lulc_feature_stack` | build a year's full candidate feature stack, list bands |
| `lulc_analyze` | correlation/VIF/importance reports (never auto-prunes) |
| `lulc_classify` | polygon-grouped CV (RF/GBT/SVM) → McNemar → GEE retrain → export |
| `lulc_collector_script` | generate the GEE Code Editor training-polygon collector |

## Design principles

- **Typed everything.** Every tool has a complete JSON schema — parameter guessing is
  a bug, and an included test fails if any tool ships an empty schema. `execute_code`
  exists as the escape hatch for the long tail (any dataset, any analysis), but the
  typed tools are the primary path: they can't produce syntax errors and their
  workflows stay reproducible.
- **Local trust model.** `execute_code` runs on your machine with your Earth Engine
  credentials — the same trust you give any local REPL. Don't expose the server to
  untrusted clients.
- **No geographic hardcoding.** Any AOI on Earth (lat/lon+radius or GeoJSON), any year
  since 1972.
- **Statistically honest.** Classification accuracy comes from polygon-grouped
  StratifiedGroupKFold CV; neighboring pixels from one polygon never straddle folds.
- **Reproducible.** The LULC tools operate on `lulc.yaml` project files; whatever an
  AI session does, a human can rerun with the `lulc` CLI from the same config.

## A worked session

1. `gee_init(project_id="my-gee-project")`
2. `catalog_search("sentinel-2 surface reflectance")` → confirm the dataset
3. `scene_availability(start_date="2022-01-01", end_date="2022-03-31", lat=-0.15, lon=37.31, radius_m=15000)`
4. `build_composite(year=2022, season_start_month=1, season_end_month=3, lat=-0.15, lon=37.31, radius_m=15000)` → `composite_1`
5. `compute_indices("composite_1", ["NDVI", "NDMI"])`
6. `thumbnail("composite_1")` → look at it
7. `thumbnail("composite_1", bands=["NDVI"], min_val=-0.1, max_val=0.8, palette=["8c510a","f6e8c3","5ab4ac","01665e"])`
8. `export_composite("composite_1", description="mtkenya_dry_2022")` → `export_tasks()`
