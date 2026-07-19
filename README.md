# geeflow

**Google Earth Engine workflows made easy — as a Python library, an MCP server for
AI-assisted analysis, and a complete land-cover classification toolkit.**

This monorepo contains two pip-installable packages:

| package | what it is |
|---------|------------|
| [`geeflow`](packages/geeflow) | Core GEE workflows: harmonized multi-sensor composites (Landsat MSS 1972 → Sentinel-2 today), cloud masking, a spectral-index registry, seasonal phenology features, thumbnails, stats, exports — plus **`geeflow-mcp`**, an MCP server that exposes all of it as fully-typed tools for Claude and other AI assistants. |
| [`lulc-engine`](packages/lulc-engine) | A complete land-use/land-cover classification use case built on geeflow: one shareable `lulc.yaml` per project, training-data management with spatially-honest cross-validation (RF/GBT/SVM + McNemar), feature analysis that never auto-prunes, and a `lulc` CLI. |

## Install

```bash
pip install "geeflow @ git+https://github.com/prahaladuk2208-arch/geeflow#subdirectory=packages/geeflow"
pip install "lulc-engine @ git+https://github.com/prahaladuk2208-arch/geeflow#subdirectory=packages/lulc-engine"
```

Or from a clone:

```bash
git clone https://github.com/prahaladuk2208-arch/geeflow
cd geeflow
pip install -e packages/geeflow -e packages/lulc-engine
```

## The MCP server

`geeflow-mcp` turns Earth Engine into a set of typed tools an AI assistant can drive:
catalog search, scene availability, harmonized composites, spectral indices,
thumbnails, region statistics, exports and task tracking. When lulc-engine is
installed, full LULC workflow tools (validate / check / analyze / classify / collector
generation) are registered too — every action stays reproducible from a `lulc.yaml` a
human can rerun.

Add it to Claude Code:

```bash
claude mcp add geeflow -- geeflow-mcp
```

or to any MCP client config:

```json
{
  "mcpServers": {
    "geeflow": { "command": "geeflow-mcp" }
  }
}
```

Design principles (learned from the rough edges of other GEE MCP servers):

- **Every tool has a complete typed parameter schema** — no guess-the-argument tools
  (this is even enforced by a test).
- **No geographic hardcoding** — any AOI on Earth, any year since 1972.
- **Statistically honest** — classification accuracy comes from polygon-grouped CV,
  not leaky pixel splits.
- **Reproducible** — workflows round-trip through config files, not opaque session state.

## Quick taste (Python API)

```python
import ee
from geeflow import Season, era_for_year
from geeflow.composite.builder import build_composites
from geeflow.features.indices import add_indices
from geeflow.geometry import point_buffer
from geeflow.session import init_ee

init_ee("my-gee-project")
aoi = point_buffer(lat=-0.15, lon=37.31, radius_m=15000)
composites, sensor, bands = build_composites(
    2022, aoi, seasons=[Season(name="dry", months=(1, 3))]
)
image, computed = add_indices(composites["dry"], ["NDVI", "NDMI"], bands)
```

For the full LULC workflow, see [packages/lulc-engine](packages/lulc-engine) and the
runnable [examples](examples/).

## Documentation

- [Quickstart (LULC workflow)](docs/quickstart.md)
- [MCP server guide](docs/mcp.md)
- [Config reference](docs/config-reference.md)
- [Training data guide](docs/training-data.md)
- [Backends](docs/backends.md)

## License

MIT
