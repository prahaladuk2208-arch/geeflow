"""Resolve the configured AOI into an ee.Geometry via geeflow's geometry helpers."""

from __future__ import annotations

from pathlib import Path

from geeflow.geometry import asset_geometry, geometry_from_file, point_buffer
from lulc_engine.config.schema import AOIConfig


def resolve_aoi(cfg: AOIConfig, base_dir: Path | None = None):
    """Build the study-area ee.Geometry from whichever AOI source the config sets."""
    if cfg.center_buffer is not None:
        cb = cfg.center_buffer
        return point_buffer(cb.lat, cb.lon, cb.radius_m)

    if cfg.geojson is not None:
        path = Path(cfg.geojson)
        if not path.is_absolute() and base_dir is not None:
            path = base_dir / path
        return geometry_from_file(path)

    return asset_geometry(cfg.ee_asset)
