"""Visualization helpers: thumbnails and web-map tiles for quick visual verification."""

from __future__ import annotations

# Sensible stretch defaults for harmonized surface reflectance (0-1)
TRUE_COLOR = {"bands": ["Red", "Green", "Blue"], "min": 0, "max": 0.3}
FALSE_COLOR_NIR = {"bands": ["NIR", "Red", "Green"], "min": 0, "max": 0.4}
NDVI_PALETTE = ["8c510a", "d8b365", "f6e8c3", "c7eae5", "5ab4ac", "01665e"]


def thumbnail_url(
    image,
    region,
    bands: list[str] | None = None,
    min_val: float = 0,
    max_val: float = 0.3,
    palette: list[str] | None = None,
    dimensions: int = 640,
) -> str:
    """A PNG thumbnail URL for an image over a region.

    Single-band images take a palette; multi-band images take exactly 3 bands.
    """
    params: dict = {"region": region, "dimensions": dimensions, "format": "png",
                    "min": min_val, "max": max_val}
    if bands:
        params["bands"] = bands
    if palette:
        params["palette"] = palette
    return image.getThumbURL(params)


def tile_url_template(image, bands: list[str] | None = None, min_val: float = 0,
                      max_val: float = 0.3, palette: list[str] | None = None) -> str:
    """An XYZ tile URL template ({z}/{x}/{y}) usable in any web map client."""
    vis: dict = {"min": min_val, "max": max_val}
    if bands:
        vis["bands"] = bands
    if palette:
        vis["palette"] = palette
    map_id = image.getMapId(vis)
    return map_id["tile_fetcher"].url_format
