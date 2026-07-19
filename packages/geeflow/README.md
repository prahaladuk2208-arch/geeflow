# geeflow

Core Google Earth Engine workflows: harmonized multi-sensor composites, spectral
indices, seasonal phenology features, thumbnails, statistics and exports — as a Python
library and as the **`geeflow-mcp`** MCP server for AI-assisted analysis.

Part of the [geeflow monorepo](https://github.com/prahaladuk2208-arch/geeflow); see the
root README for the full picture and the `lulc-engine` package for the land-cover
classification toolkit built on top.

## Highlights

- **Any year since 1972**: sensor eras (Landsat MSS → TM/ETM+ → OLI → Sentinel-2) are
  resolved automatically with era-appropriate scales, cloud masks and band
  harmonization to standard names (`Blue/Green/Red/NIR/SWIR1/SWIR2/...`).
- **Scene-count fallbacks**: sparse archives trigger backup sensors and wider date
  windows automatically.
- **Index registry**: NDVI, SAVI, EVI, NDMI, NBR, NDWI, NDBI, red-edge indices — an
  index is only computed when its required bands exist in the era.
- **MCP server**: `geeflow-mcp` exposes everything as fully-typed tools
  (catalog search, composites, thumbnails, stats, exports, task tracking).

## Install

```bash
pip install "geeflow @ git+https://github.com/prahaladuk2208-arch/geeflow#subdirectory=packages/geeflow"
```

## MCP setup

```bash
claude mcp add geeflow -- geeflow-mcp
```

See [docs/mcp.md](https://github.com/prahaladuk2208-arch/geeflow/blob/main/docs/mcp.md)
for the tool list and a worked session.
