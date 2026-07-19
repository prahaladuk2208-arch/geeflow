# geeflow

**Google Earth Engine workflows made easy — a Python library, an MCP server so AI
assistants can drive Earth Engine, and a complete land-cover classification toolkit.**

Building a cloud-free satellite composite of anywhere on Earth for any year since 1972
should be one function call, not a hundred lines of boilerplate about sensor choice,
cloud masks, band names and scaling factors. Making a land-use/land-cover (LULC) map
should be a config file, not a bespoke script. That's what this repo does.

## What's inside

| package | what it is |
|---------|------------|
| [`geeflow`](packages/geeflow) | Core GEE workflows: automatic sensor selection per year (Landsat MSS 1972 → TM/ETM+ → OLI → Sentinel-2 today), cloud masking, band harmonization to one common naming, seasonal median composites with scene-count fallbacks, a spectral-index registry (NDVI, SAVI, EVI, NDMI, NBR, NDWI, NDBI, red-edge), thumbnails/tiles, region statistics, Drive/asset exports, catalog search — plus **`geeflow-mcp`**, an MCP server exposing all of it as fully-typed tools. |
| [`lulc-engine`](packages/lulc-engine) | A complete LULC classification workflow built on geeflow: one shareable `lulc.yaml` per project, training-polygon management, honest accuracy via polygon-grouped cross-validation (RF/GBT/SVM + McNemar's test), feature analysis that never auto-prunes, post-processing, exports, and a `lulc` CLI. |

## What you need

- **Python ≥ 3.10** (Windows, macOS, Linux)
- **A Google Earth Engine account** (free for research/non-commercial —
  [sign up](https://earthengine.google.com/)) and a Google Cloud project with the
  Earth Engine API enabled
- Nothing else: all imagery processing runs server-side in Earth Engine, so no big
  downloads and no GPU

## Install

From a clone (recommended while pre-release):

```bash
git clone https://github.com/prahaladuk2208-arch/geeflow
cd geeflow
pip install -e packages/geeflow -e packages/lulc-engine
```

Or straight from GitHub:

```bash
pip install "geeflow @ git+https://github.com/prahaladuk2208-arch/geeflow#subdirectory=packages/geeflow"
pip install "lulc-engine @ git+https://github.com/prahaladuk2208-arch/geeflow#subdirectory=packages/lulc-engine"
```

Authenticate Earth Engine once:

```bash
earthengine authenticate        # or: lulc auth
```

## How to use it

### Option A — let an AI assistant drive it (MCP)

```bash
claude mcp add geeflow -- geeflow-mcp
```

Then just talk: *"Build a cloud-free dry-season composite of the Mount Kenya area for
2022, show me a thumbnail, and tell me which sensors were available."* The assistant
gets 10 typed core tools (catalog search, scene availability, composites, indices,
thumbnails, stats, exports, task tracking) and — when lulc-engine is installed — 6
LULC workflow tools. Full guide: [docs/mcp.md](docs/mcp.md).

### Option B — the `lulc` CLI (config-driven classification)

```bash
lulc init --template forest    # scaffold lulc.yaml + folders
# edit lulc.yaml: your AOI, GEE project id, classes, seasons, years
lulc validate -c lulc.yaml     # resolved year -> sensor/era plan
lulc check -c lulc.yaml        # scene availability
lulc labels template -c lulc.yaml --year 2022   # generates the polygon-drawing tool
lulc analyze -c lulc.yaml --year 2022           # correlation/VIF/importance reports
lulc classify -c lulc.yaml --year 2022          # CV -> best model -> map -> Drive
```

The whole project is the `lulc.yaml` plus a training folder — send both to a
collaborator and they reproduce your map exactly. Start from the runnable
[examples](examples/): a 4-class Sentinel-2 workflow and a Landsat time series
reaching back to 1978.

### Option C — the Python API

```python
from geeflow import Season
from geeflow.composite.builder import build_composites
from geeflow.features.indices import add_indices
from geeflow.geometry import point_buffer
from geeflow.session import init_ee

init_ee("my-gee-project")
aoi = point_buffer(lat=-0.15, lon=37.31, radius_m=15000)
composites, sensor, bands = build_composites(
    2022, aoi, seasons=[Season(name="dry", months=(1, 3))]
)
ndvi_ready, computed = add_indices(composites["dry"], ["NDVI", "NDMI"], bands)
```

## Design principles

- **Typed everything.** Every MCP tool has a complete JSON schema; a test fails the
  build if any tool ships an empty one.
- **No geographic hardcoding.** Any AOI on Earth, any year since 1972; sensor eras,
  scales and cloud masks resolve automatically.
- **Statistically honest.** Classification accuracy comes from polygon-grouped
  StratifiedGroupKFold CV — pixels from one training polygon never straddle folds —
  plus McNemar's test between competing models.
- **Never auto-prune.** Feature analysis reports correlation/VIF/importance evidence;
  the human decides what to drop.
- **Reproducible.** Workflows round-trip through config files, not opaque session
  state; whatever an AI session does, a human can rerun with the CLI.

## Testing

`pytest` (65 unit tests, no GEE account needed — the `ee` module is mocked) plus
opt-in live integration tests (`LULC_GEE_TESTS=1 LULC_GEE_PROJECT=<id> pytest -m gee`)
and an end-to-end MCP stdio protocol test. CI runs lint + tests on Windows and Linux,
Python 3.10–3.14.

## Documentation

- [Quickstart (LULC workflow)](docs/quickstart.md)
- [MCP server guide](docs/mcp.md)
- [Config reference](docs/config-reference.md)
- [Training data guide](docs/training-data.md)
- [Backends](docs/backends.md)

## Roadmap

- **M2** — shapefile/KML/GPX/CSV training import; training labels sampled from public
  LULC products (Dynamic World, ESA WorldCover, Hansen GFC) with consensus logic;
  satellite-embedding features; local GeoTIFF backend (rasterio + scikit-learn).
- **M3** — OpenStreetMap land-use ingest; STAC imagery backend (Planetary Computer /
  Earth Search); change-detection helpers.

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
