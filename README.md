# geeflow

**An MCP server that lets Claude run Google Earth Engine.**

Ask Claude to build a cloud-free satellite image of anywhere on Earth, compute
vegetation indices, pull statistics, or classify land cover, and it actually does it on
Google's servers. geeflow is the connector that makes that work: a Model Context
Protocol (MCP) server exposing Earth Engine as a set of typed tools, plus a code tool so
Claude can run arbitrary Earth Engine Python when a task needs something custom.

Underneath the MCP server is a full Python toolkit (usable on its own via CLI or import),
so anything an AI session does, a human can reproduce.

## What it does

Through Claude (or any MCP client), geeflow can:

- **Find data**: search the Earth Engine catalog (880+ datasets) and read dataset metadata
- **Build imagery**: cloud-free, harmonized composites for any place and any year since
  1972. It picks the right satellite for the year (Landsat MSS through Sentinel-2), cloud
  masks, renames bands to one common scheme, and falls back to backup sensors or wider
  date windows when scenes are scarce
- **Analyse**: spectral indices (NDVI, SAVI, EVI, NDMI, NBR, NDWI, NDBI, red-edge),
  per-region statistics, scene availability
- **See it**: PNG thumbnail links so you and Claude can look at the result
- **Training data**: auto-generate labeled polygons from land-cover products like ESA
  WorldCover
- **Classify**: a full land-cover classification workflow with honest, leakage-safe
  accuracy (optional, see below)
- **Export**: send results to Google Drive or an Earth Engine asset, and track the jobs
- **Anything else**: an `execute_code` tool runs arbitrary Earth Engine Python for
  datasets and analyses the typed tools do not cover (climate, rainfall, temperature,
  terrain, custom reducers)

## What you need

- **Python 3.10 or newer** (Windows, macOS, Linux)
- **A Google Earth Engine account** (free for research and non-commercial use,
  [sign up here](https://earthengine.google.com/)) and a Google Cloud project with the
  Earth Engine API enabled
- Nothing else. All the heavy computation runs on Google's servers, so no big downloads
  and no GPU. Your credentials stay on your machine.

## Quick start (with Claude)

```bash
# 1. install the MCP server
pip install "geeflow @ git+https://github.com/prahaladuk2208-arch/geeflow#subdirectory=packages/geeflow"

# 2. authenticate Earth Engine once (opens a browser)
earthengine authenticate

# 3. add the server to Claude Code
claude mcp add geeflow -- geeflow-mcp
```

For Claude Desktop or another MCP client, point it at the `geeflow-mcp` command instead:

```json
{
  "mcpServers": {
    "geeflow": { "command": "geeflow-mcp" }
  }
}
```

Then start a session and just ask. A first message tells Claude your project:

> Use geeflow. My Earth Engine project is my-gee-project. Build a cloud-free dry-season
> composite of the area around Mount Kenya for 2022, show me a thumbnail, then tell me
> the mean NDVI.

Claude will call `gee_init`, `build_composite`, `compute_indices`, `thumbnail` and
`region_stats` in order and hand back a viewable image and a number.

## The tools

**Core Earth Engine tools** (installed with `geeflow`):

| tool | what it does |
|------|--------------|
| `gee_init` | connect to Earth Engine (call once per session) |
| `catalog_search` | keyword search across the data catalog |
| `dataset_info` | metadata for a dataset id |
| `scene_availability` | scene counts per sensor for a place and date range |
| `build_composite` | cloud-free, harmonized composite for a year and month window |
| `compute_indices` | add spectral index bands |
| `thumbnail` | PNG preview URL |
| `region_stats` | per-band mean / median / min-max / stdDev over the region |
| `sample_polygons` | auto-generate labeled training polygons from a land-cover product |
| `export_composite` | export to Google Drive or an Earth Engine asset |
| `export_tasks` | recent export jobs and their states |
| `execute_code` | run arbitrary Earth Engine Python for anything above tools do not cover |

**Land-cover classification tools** appear automatically when the optional `lulc-engine`
package is also installed (`lulc_validate`, `lulc_check`, `lulc_feature_stack`,
`lulc_analyze`, `lulc_classify`, `lulc_collector_script`). See
[docs/mcp.md](docs/mcp.md) for a full worked session.

## Using it without AI

The same engine works as a normal library and CLI, so nothing depends on an AI being in
the loop.

Python:

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
with_indices, computed = add_indices(composites["dry"], ["NDVI", "NDMI"], bands)
```

Land-cover classification from a config file (install the optional package first,
`pip install "lulc-engine @ git+https://github.com/prahaladuk2208-arch/geeflow#subdirectory=packages/lulc-engine"`):

```bash
lulc init --template forest    # scaffold a lulc.yaml + folders
lulc validate -c lulc.yaml     # resolved year to sensor plan
lulc classify -c lulc.yaml --year 2022   # CV, best model, map, export
```

## What is in the repo

Two pip-installable packages:

- **`geeflow`** (`packages/geeflow`): the core Earth Engine toolkit and the MCP server.
- **`lulc-engine`** (`packages/lulc-engine`): an optional land-cover classification
  workflow built on geeflow. One `lulc.yaml` defines a whole project (area, years,
  classes, seasons); it compares Random Forest, Gradient Boosting and SVM with
  polygon-grouped cross-validation, then exports the map. Send the config to a
  collaborator and they reproduce your result.

## Design principles

- **Typed first, with an escape hatch.** Every tool has a complete JSON schema, and a
  test fails the build if any tool ships an empty one. `execute_code` covers the long
  tail so the server is a real connector, not a fixed menu.
- **No geographic hardcoding.** Any area on Earth, any year since 1972. Sensor eras,
  scales and cloud masks resolve automatically.
- **Runs locally, with your credentials.** `execute_code` executes on your machine with
  your Earth Engine login, the same trust as any local Python session. Do not expose the
  server to untrusted clients.
- **Statistically honest.** Classification accuracy comes from polygon-grouped
  cross-validation (pixels from one training polygon never straddle folds) plus McNemar's
  test between models.
- **Reproducible.** Workflows round-trip through config files, so whatever an AI session
  does, a human can rerun with the CLI.

## Testing

69 unit tests run with no Earth Engine account needed (the `ee` module is mocked), plus
opt-in live integration tests against real Earth Engine and an end-to-end MCP protocol
test. CI runs lint and tests on Windows and Linux, Python 3.10 to 3.14. The bundled
example classifies at about 95 percent accuracy on real imagery.

## Documentation

- [MCP server guide](docs/mcp.md)
- [Quickstart (classification workflow)](docs/quickstart.md)
- [Config reference](docs/config-reference.md)
- [Training data guide](docs/training-data.md)

## Roadmap

- **M2**: shapefile / KML / GPX / CSV training import, training labels from public
  land-cover products (Dynamic World, ESA WorldCover, Hansen) with consensus logic,
  satellite-embedding features, local GeoTIFF backend.
- **M3**: OpenStreetMap land-use ingest, STAC imagery backend, change-detection helpers.

Contributions welcome, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
