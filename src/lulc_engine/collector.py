"""Render the GEE Code Editor training-polygon collector script from config.

Replaces the practice of hand-copying one JS file per year: the AOI, sensor, seasons
and class scheme all come from lulc.yaml, so collectors stay in sync with the pipeline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Environment, PackageLoader

from lulc_engine.composite.builder import sensors_for
from lulc_engine.config.schema import LulcConfig
from lulc_engine.sensors.harmonize import harmonized_bands_for
from lulc_engine.sensors.registry import (
    COLLECTIONS,
    LANDSAT57_BAND_MAP,
    LANDSAT89_BAND_MAP,
    MSS_BAND_MAP,
    SENTINEL2_BAND_MAP,
)
from lulc_engine.utils.dates import season_date_range

_SENSOR_LABELS = {
    "sentinel2_sr": "Sentinel-2 SR",
    "landsat5_t1_sr": "Landsat 5 TM",
    "landsat7_t1_sr": "Landsat 7 ETM+",
    "landsat8_sr": "Landsat 8 OLI",
    "landsat9_sr": "Landsat 9 OLI",
}


def _sanitize_var(name: str) -> str:
    var = re.sub(r"[^0-9a-zA-Z]", "", name)
    if not var or var[0].isdigit():
        var = "Class" + var
    return var


def _era_kind(sensor_key: str) -> str:
    if sensor_key == "sentinel2_sr":
        return "s2"
    if sensor_key.startswith("landsat_mss_"):
        return "mss"
    return "landsat_sr"


def _band_maps(sensor_key: str) -> dict:
    if sensor_key == "sentinel2_sr":
        return SENTINEL2_BAND_MAP
    if sensor_key in ("landsat5_t1_sr", "landsat7_t1_sr"):
        return LANDSAT57_BAND_MAP
    if sensor_key in ("landsat8_sr", "landsat9_sr"):
        return LANDSAT89_BAND_MAP
    return MSS_BAND_MAP


def render_collector(cfg: LulcConfig, year: int) -> str:
    era = cfg.era_for_year(year)
    sensor_key = sensors_for(year, era)[0]
    band_map = _band_maps(sensor_key)

    aoi_kind = (
        "center_buffer"
        if cfg.aoi.center_buffer
        else ("ee_asset" if cfg.aoi.ee_asset else "geojson")
    )
    geojson_geometry = None
    if aoi_kind == "geojson":
        path = cfg.aoi.geojson
        if not Path(path).is_absolute():
            path = cfg.base_dir / path
        with open(path, encoding="utf-8") as f:
            gj = json.load(f)
        if gj.get("type") == "FeatureCollection":
            gj = gj["features"][0]["geometry"]
        elif gj.get("type") == "Feature":
            gj = gj["geometry"]
        geojson_geometry = json.dumps(gj)

    seasons = []
    for s in cfg.seasons:
        start, end = season_date_range(year, s)
        seasons.append({"name": s.name, "var": f"season_{_sanitize_var(s.name)}", "start": start, "end": end})
    ref_name = cfg.reference_season.name
    ref_var = next(s["var"] for s in seasons if s["name"] == ref_name)
    others = [s for s in seasons if s["name"] != ref_name]
    other = others[0] if others else None

    classes = [
        {"code": code, "name": name, "var": _sanitize_var(name)}
        for code, name in cfg.sorted_class_items()
    ]
    merge_expr = classes[0]["var"]
    for c in classes[1:]:
        merge_expr = f"{merge_expr}.merge({c['var']})"

    filename = Path(cfg.training.path.format(year=year)).name

    env = Environment(loader=PackageLoader("lulc_engine", "templates"), keep_trailing_newline=True)
    template = env.get_template("training_collector.js.j2")
    return template.render(
        year=year,
        project_name=cfg.project.name,
        sensor_label=_SENSOR_LABELS.get(sensor_key, sensor_key),
        class_property=cfg.training.class_property,
        classes=classes,
        merge_expr=merge_expr,
        filename=filename,
        drive_folder=cfg.export.folder,
        aoi_kind=aoi_kind,
        lon=cfg.aoi.center_buffer.lon if cfg.aoi.center_buffer else None,
        lat=cfg.aoi.center_buffer.lat if cfg.aoi.center_buffer else None,
        radius_m=cfg.aoi.center_buffer.radius_m if cfg.aoi.center_buffer else None,
        ee_asset=cfg.aoi.ee_asset,
        geojson_geometry=geojson_geometry,
        era_kind=_era_kind(sensor_key),
        collection_id=COLLECTIONS[sensor_key],
        select_src=json.dumps(list(band_map.keys())),
        select_dst=json.dumps(list(band_map.values())),
        seasons=seasons,
        ref_var=ref_var,
        ref_name=ref_name,
        other_var=other["var"] if other else None,
        other_name=other["name"] if other else None,
        has_swir="SWIR1" in harmonized_bands_for(sensor_key),
        scale=era.scale_m,
    )
