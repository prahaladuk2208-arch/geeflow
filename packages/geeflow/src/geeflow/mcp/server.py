"""The geeflow MCP server: Google Earth Engine workflows as typed tools.

Run with `geeflow-mcp` (stdio transport). Every tool has a complete, typed parameter
schema — no guess-the-argument tools. Composites built during a session are held in
an in-memory registry and referenced by id in follow-up calls (indices, thumbnails,
stats, exports).

When lulc-engine is installed, LULC workflow tools (validate / check / analyze /
classify / collector) are registered as well; each wraps a lulc.yaml project config so
everything an AI session does remains reproducible from a file a human can rerun.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "geeflow",
    instructions=(
        "Google Earth Engine workflows: catalog search, harmonized multi-sensor "
        "composites, spectral indices, thumbnails, stats and exports. Call gee_init "
        "first. Composite tools return a composite_id used by later calls."
    ),
)

# Session registry: composite_id -> {image, region, scale, bands}
_COMPOSITES: dict[str, dict] = {}
_COUNTER = {"n": 0}


def _register(image, region, scale: int, bands: list[str]) -> str:
    _COUNTER["n"] += 1
    cid = f"composite_{_COUNTER['n']}"
    _COMPOSITES[cid] = {"image": image, "region": region, "scale": scale, "bands": bands}
    return cid


def _get(composite_id: str) -> dict:
    if composite_id not in _COMPOSITES:
        raise ValueError(
            f"unknown composite_id {composite_id!r}; known: {list(_COMPOSITES) or 'none — call build_composite first'}"
        )
    return _COMPOSITES[composite_id]


def _resolve_region(lat: float | None, lon: float | None, radius_m: float | None,
                    aoi_geojson: str | None):
    from geeflow.geometry import geometry_from_geojson, point_buffer

    if aoi_geojson:
        return geometry_from_geojson(json.loads(aoi_geojson))
    if lat is not None and lon is not None:
        return point_buffer(lat, lon, radius_m or 10_000)
    raise ValueError("provide either aoi_geojson or lat+lon (+optional radius_m)")


# --------------------------------------------------------------------- core tools


@mcp.tool()
def gee_init(project_id: str | None = None, service_account_key: str | None = None) -> str:
    """Initialize Earth Engine. Call this first in every session.

    Args:
        project_id: Google Cloud project with Earth Engine enabled.
        service_account_key: path to a service-account key JSON (optional; otherwise
            cached user credentials from `earthengine authenticate` are used).
    """
    from geeflow.session import init_ee

    init_ee(project_id, service_account_key)
    return f"Earth Engine initialized (project={project_id or 'default credentials'})"


@mcp.tool()
def catalog_search(query: str, limit: int = 10) -> list[dict]:
    """Search the Earth Engine data catalog by keywords.

    Args:
        query: space-separated terms matched against dataset id/title/tags/provider,
            e.g. "sentinel-2 surface reflectance" or "land cover 10m".
        limit: maximum results.
    """
    from geeflow.catalog import search

    return search(query, limit)


@mcp.tool()
def dataset_info(dataset_id: str) -> dict:
    """Catalog metadata for an exact dataset id (e.g. "COPERNICUS/S2_SR_HARMONIZED")."""
    from geeflow.catalog import dataset_entry

    entry = dataset_entry(dataset_id)
    if entry is None:
        raise ValueError(f"dataset {dataset_id!r} not found in the catalog index")
    return entry


@mcp.tool()
def scene_availability(
    start_date: str,
    end_date: str,
    lat: float | None = None,
    lon: float | None = None,
    radius_m: float | None = None,
    aoi_geojson: str | None = None,
    sensors: list[str] | None = None,
) -> dict:
    """Count available scenes per sensor over a region and date range.

    Args:
        start_date / end_date: ISO dates (YYYY-MM-DD).
        lat, lon, radius_m: circular region (radius defaults to 10 km) — or pass
            aoi_geojson instead.
        aoi_geojson: GeoJSON string (Feature/FeatureCollection/geometry).
        sensors: sensor keys (see geeflow COLLECTIONS); default = the era-appropriate
            sensors for the start year (e.g. sentinel2_sr + landsat9_sr for recent dates).
    """
    from geeflow.composite.builder import sensors_for
    from geeflow.sensors.harmonize import get_collection
    from geeflow.specs import era_for_year

    region = _resolve_region(lat, lon, radius_m, aoi_geojson)
    year = int(start_date[:4])
    keys = sensors or sensors_for(year, era_for_year(year))
    counts = {sk: get_collection(sk, region, start_date, end_date).size().getInfo() for sk in keys}
    return {"start_date": start_date, "end_date": end_date, "scene_counts": counts}


@mcp.tool()
def build_composite(
    year: int,
    season_start_month: int = 1,
    season_end_month: int = 12,
    lat: float | None = None,
    lon: float | None = None,
    radius_m: float | None = None,
    aoi_geojson: str | None = None,
    reducer: str = "median",
    min_scenes: int = 3,
) -> dict:
    """Build a cloud-masked, harmonized composite for a year and month window.

    The sensor is chosen automatically from the year (Landsat MSS era through 1983 at
    60 m, TM/ETM+/OLI through 2013 at 30 m, Sentinel-2 after at 10 m), scenes are
    cloud-masked, bands renamed to standard names (Blue/Green/Red/NIR/SWIR1/SWIR2...),
    with automatic fallbacks (backup sensor, wider date window) when scenes are scarce.

    A month window with start > end (e.g. 11 to 2) wraps into the next year.
    Returns a composite_id for use with compute_indices / thumbnail / region_stats /
    export_composite, plus the sensor, bands and native scale.
    """
    from geeflow.composite.builder import build_composites
    from geeflow.specs import CompositeSpec, Season, era_for_year

    region = _resolve_region(lat, lon, radius_m, aoi_geojson)
    season = Season(name="window", months=(season_start_month, season_end_month))
    logs: list[str] = []
    composites, sensor, bands = build_composites(
        year,
        region,
        seasons=[season],
        spec=CompositeSpec(reducer=reducer, min_scenes=min_scenes),
        log=logs.append,
    )
    scale = era_for_year(year).scale_m
    cid = _register(composites["window"], region, scale, list(bands))
    return {
        "composite_id": cid,
        "sensor": sensor,
        "bands": bands,
        "scale_m": scale,
        "log": "\n".join(line.strip() for line in logs if line.strip()),
    }


@mcp.tool()
def compute_indices(composite_id: str, indices: list[str]) -> dict:
    """Add spectral index bands to a composite.

    Args:
        composite_id: from build_composite.
        indices: from NDVI, SAVI, EVI, NDMI, NBR, BlueGreenNIR, GreenRed, NDRE, CIre,
            NDWI, NDBI. Indices whose required bands are missing in this sensor era are
            skipped and reported.
    """
    from geeflow.features.indices import add_indices

    entry = _get(composite_id)
    image, computed = add_indices(entry["image"], indices, entry["bands"])
    entry["image"] = image
    entry["bands"] = entry["bands"] + computed
    skipped = [i for i in indices if i not in computed]
    return {"composite_id": composite_id, "computed": computed, "skipped": skipped,
            "bands": entry["bands"]}


@mcp.tool()
def thumbnail(
    composite_id: str,
    bands: list[str] | None = None,
    min_val: float = 0,
    max_val: float = 0.3,
    palette: list[str] | None = None,
    dimensions: int = 640,
) -> dict:
    """A PNG thumbnail URL for visual inspection.

    Defaults to true color (Red/Green/Blue). For a single-band layer (e.g. ["NDVI"])
    pass min/max for the stretch and optionally a palette of hex colors.
    """
    from geeflow.viz import thumbnail_url

    entry = _get(composite_id)
    url = thumbnail_url(
        entry["image"], entry["region"],
        bands=bands or ["Red", "Green", "Blue"],
        min_val=min_val, max_val=max_val, palette=palette, dimensions=dimensions,
    )
    return {"url": url, "note": "open in a browser; link expires after a while"}


@mcp.tool()
def region_stats(composite_id: str, reducer: str = "mean", bands: list[str] | None = None) -> dict:
    """Per-band statistics over the composite's region (reducer: mean, median, minMax, stdDev)."""
    import ee

    entry = _get(composite_id)
    reducers = {
        "mean": ee.Reducer.mean(),
        "median": ee.Reducer.median(),
        "minMax": ee.Reducer.minMax(),
        "stdDev": ee.Reducer.stdDev(),
    }
    if reducer not in reducers:
        raise ValueError(f"reducer must be one of {list(reducers)}")
    image = entry["image"].select(bands) if bands else entry["image"]
    stats = image.reduceRegion(
        reducer=reducers[reducer],
        geometry=entry["region"],
        scale=entry["scale"],
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    return {"reducer": reducer, "stats": stats}


@mcp.tool()
def export_composite(
    composite_id: str,
    description: str,
    target: str = "drive",
    folder: str = "geeflow_outputs",
    asset_root: str | None = None,
    scale: int | None = None,
    crs: str = "EPSG:4326",
) -> dict:
    """Export a composite to Google Drive (target="drive") or an EE asset (target="asset").

    Returns the task id; check progress with export_tasks.
    """
    from geeflow.export import export_image

    entry = _get(composite_id)
    logs: list[str] = []
    task = export_image(
        entry["image"], entry["region"], description,
        target=target, folder=folder, asset_root=asset_root,
        scale=scale or entry["scale"], crs=crs, log=logs.append,
    )
    return {"task_id": task.id, "description": description,
            "monitor": "https://code.earthengine.google.com/tasks"}


@mcp.tool()
def export_tasks(limit: int = 10) -> list[dict]:
    """Recent Earth Engine export tasks with their states (READY/RUNNING/COMPLETED/FAILED)."""
    from geeflow.tasks import list_tasks

    return list_tasks(limit)


# --------------------------------------------------------------- LULC tools (optional)

try:
    import lulc_engine  # noqa: F401

    _HAS_LULC = True
except ImportError:
    _HAS_LULC = False


if _HAS_LULC:

    def _pipeline(config_path: str, logs: list[str]):
        from lulc_engine.config import load_config
        from lulc_engine.pipeline import Pipeline

        return Pipeline(load_config(config_path), initialize=False, log=logs.append)

    @mcp.tool()
    def lulc_validate(config_path: str) -> dict:
        """Validate a lulc.yaml project config and return the resolved run plan.

        Args:
            config_path: path to the project's lulc.yaml.
        """
        from geeflow.composite.builder import sensors_for
        from lulc_engine.config import load_config

        cfg = load_config(config_path)
        return {
            "project": cfg.project.name,
            "classes": dict(cfg.sorted_class_items()),
            "seasons": [{"name": s.name, "months": list(s.months)} for s in cfg.seasons],
            "reference_season": cfg.reference_season.name,
            "indices": cfg.features.indices,
            "run_plan": [
                {
                    "year": y,
                    "era": cfg.era_for_year(y).name,
                    "scale_m": cfg.scale_for_year(y),
                    "sensors": sensors_for(y, cfg.era_for_year(y)),
                }
                for y in cfg.time_points
            ],
        }

    @mcp.tool()
    def lulc_check(config_path: str, years: list[int] | None = None) -> dict:
        """Scene availability per configured year/season/sensor for a lulc.yaml project."""
        logs: list[str] = []
        pipe = _pipeline(config_path, logs)
        report = pipe.check(years)
        return {"availability": report}

    @mcp.tool()
    def lulc_feature_stack(config_path: str, year: int) -> dict:
        """Build the year's full candidate feature stack and return its band names."""
        logs: list[str] = []
        pipe = _pipeline(config_path, logs)
        stack = pipe.build_features(year)
        bands = stack.bandNames().getInfo()
        return {"year": year, "n_bands": len(bands), "bands": bands,
                "scale_m": pipe.cfg.scale_for_year(year)}

    @mcp.tool()
    def lulc_analyze(config_path: str, year: int) -> dict:
        """Correlation/VIF/importance analysis for a year. Reports only — never prunes.

        Writes the correlation heatmap PNG and VIF/importance CSVs to the project's
        output_dir and returns their paths plus the flagged correlated pairs.
        """
        logs: list[str] = []
        pipe = _pipeline(config_path, logs)
        result = pipe.analyze(year)
        return {
            "artifacts": {k: str(v) for k, v in result["paths"].items()},
            "correlated_pairs": [
                {"a": a, "b": b, "r": round(r, 3)} for a, b, r in result["correlated_pairs"]
            ],
            "top_importance": result["importance"].head(10).to_dict("records"),
            "note": "Review the reports, then write selected_features_{year}.json "
                    "next to the config to prune. Nothing is pruned automatically.",
        }

    @mcp.tool()
    def lulc_classify(config_path: str, year: int, export: bool = True) -> dict:
        """Full classification for a year: polygon-grouped CV over RF/GBT/SVM, McNemar
        test, native GEE retrain of the best model, majority filter, optional export.

        Returns per-model accuracies, the winner, and the JSON report path.
        """
        logs: list[str] = []
        pipe = _pipeline(config_path, logs)
        result = pipe.classify(year, export=export)
        summary = {
            name: {
                "mean_accuracy": round(r["mean_accuracy"], 4),
                "mean_kappa": round(r["mean_kappa"], 4),
            }
            for name, r in result["results"].items()
        }
        return {
            "year": year,
            "best_classifier": result["best_classifier"],
            "cv_results": summary,
            "report_path": str(result["report_path"]),
            "export_started": export,
            "log_tail": "\n".join(logs[-25:]),
        }

    @mcp.tool()
    def lulc_collector_script(config_path: str, year: int) -> str:
        """Generate the GEE Code Editor training-polygon collector script for a year.

        Paste the returned JavaScript into https://code.earthengine.google.com/ to draw
        and export training polygons bound to the project's AOI, sensor and classes.
        """
        from lulc_engine.collector import render_collector
        from lulc_engine.config import load_config

        return render_collector(load_config(config_path), year)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
