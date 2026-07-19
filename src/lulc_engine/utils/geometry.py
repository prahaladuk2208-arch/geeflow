"""AOI resolution. The single place where geometries are built from config.

Convention: Earth Engine takes (longitude, latitude); display/print order is
(latitude, longitude). Keep that translation here, not in callers.
"""

from __future__ import annotations

import json
from pathlib import Path

import ee

from lulc_engine.config.schema import AOIConfig


def resolve_aoi(cfg: AOIConfig, base_dir: Path | None = None):
    """Build the study-area ee.Geometry from whichever AOI source the config sets."""
    if cfg.center_buffer is not None:
        cb = cfg.center_buffer
        return ee.Geometry.Point([cb.lon, cb.lat]).buffer(cb.radius_m)

    if cfg.geojson is not None:
        path = Path(cfg.geojson)
        if not path.is_absolute() and base_dir is not None:
            path = base_dir / path
        with open(path, encoding="utf-8") as f:
            gj = json.load(f)
        return _geometry_from_geojson(gj)

    return ee.FeatureCollection(cfg.ee_asset).geometry()


def _geometry_from_geojson(gj: dict):
    """Accept a Feature, FeatureCollection, or bare geometry object."""
    gtype = gj.get("type")
    if gtype == "FeatureCollection":
        feats = gj["features"]
        if not feats:
            raise ValueError("AOI FeatureCollection has no features")
        if len(feats) == 1:
            return ee.Geometry(feats[0]["geometry"])
        return ee.FeatureCollection(
            [ee.Feature(ee.Geometry(f["geometry"])) for f in feats]
        ).geometry()
    if gtype == "Feature":
        return ee.Geometry(gj["geometry"])
    return ee.Geometry(gj)


def display_coords(lon: float, lat: float) -> tuple[float, float]:
    """(lat, lon) for human-facing output."""
    return (lat, lon)
