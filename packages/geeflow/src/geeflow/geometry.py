"""Geometry construction helpers.

Convention: Earth Engine takes (longitude, latitude); display/print order is
(latitude, longitude). Keep that translation here, not in callers.
"""

from __future__ import annotations

import json
from pathlib import Path

import ee


def point_buffer(lat: float, lon: float, radius_m: float):
    """A circular study area around a point."""
    return ee.Geometry.Point([lon, lat]).buffer(radius_m)


def geometry_from_geojson(gj: dict):
    """Accept a Feature, FeatureCollection, or bare geometry object."""
    gtype = gj.get("type")
    if gtype == "FeatureCollection":
        feats = gj["features"]
        if not feats:
            raise ValueError("FeatureCollection has no features")
        if len(feats) == 1:
            return ee.Geometry(feats[0]["geometry"])
        return ee.FeatureCollection(
            [ee.Feature(ee.Geometry(f["geometry"])) for f in feats]
        ).geometry()
    if gtype == "Feature":
        return ee.Geometry(gj["geometry"])
    return ee.Geometry(gj)


def geometry_from_file(path: str | Path):
    """Load an ee.Geometry from a GeoJSON file."""
    with open(path, encoding="utf-8") as f:
        return geometry_from_geojson(json.load(f))


def asset_geometry(asset_id: str):
    """The union geometry of an Earth Engine FeatureCollection asset."""
    return ee.FeatureCollection(asset_id).geometry()


def display_coords(lon: float, lat: float) -> tuple[float, float]:
    """(lat, lon) for human-facing output."""
    return (lat, lon)
