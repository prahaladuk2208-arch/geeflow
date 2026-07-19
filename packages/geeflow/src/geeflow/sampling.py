"""Sample reference polygons from categorical land-cover products.

Generates training polygons automatically from any categorical GEE dataset (ESA
WorldCover, Dynamic World composites, national maps...). Points are drawn from
homogeneous patches (a strict neighborhood-uniformity filter that relaxes in steps so
patchy classes like cropland and built-up still yield samples) and turned into small
squares suitable for classifier training.
"""

from __future__ import annotations

import math


def sample_reference_polygons(
    dataset_id: str,
    band: str,
    class_values: list[int],
    region,
    class_labels: list[str] | None = None,
    points_per_class: int = 6,
    polygon_size_m: float = 180,
    scale: int = 10,
    homogeneity_ladder: tuple[int, ...] = (100, 50, 30),
    seed: int = 42,
    class_property: str = "class",
    is_collection: bool = True,
) -> dict:
    """Return a GeoJSON FeatureCollection of labeled square polygons.

    Args:
        dataset_id: GEE image or image-collection id (e.g. "ESA/WorldCover/v200").
        band: the categorical band (e.g. "Map").
        class_values: pixel values in the source dataset to sample; output class codes
            are their positions in this list (0, 1, 2, ...).
        region: ee.Geometry to sample within.
        class_labels: optional human-readable names, parallel to class_values.
        points_per_class: polygons wanted per class.
        polygon_size_m: side length of the output squares.
        scale: sampling scale in meters.
        homogeneity_ladder: neighborhood radii; sampling starts strict and relaxes
            until every class has at least ceil(points_per_class / 2) samples.
        is_collection: dataset_id is an ImageCollection (mosaicked) vs a single Image.
    """
    import ee

    if is_collection:
        image = ee.ImageCollection(dataset_id).mosaic().select(band)
    else:
        image = ee.Image(dataset_id).select(band)

    codes = list(range(len(class_values)))
    labels = class_labels or [str(v) for v in class_values]
    remapped = image.remap(class_values, codes).rename("cls")

    by_class: dict[int, list] = {c: [] for c in codes}
    for radius in homogeneity_ladder:
        uniform = image.focalMin(radius, "square", "meters").eq(
            image.focalMax(radius, "square", "meters")
        )
        sampled = (
            remapped.updateMask(uniform)
            .stratifiedSample(
                numPoints=points_per_class,
                classBand="cls",
                region=region,
                scale=scale,
                seed=seed,
                geometries=True,
            )
            .getInfo()["features"]
        )
        for feat in sampled:
            code = int(feat["properties"]["cls"])
            if len(by_class[code]) < points_per_class:
                by_class[code].append(feat["geometry"]["coordinates"])
        if all(len(v) >= max(1, math.ceil(points_per_class / 2)) for v in by_class.values()):
            break

    features = []
    for code in codes:
        for lon, lat in by_class[code]:
            half_lat = (polygon_size_m / 2) / 111_320
            half_lon = half_lat / max(0.01, math.cos(math.radians(lat)))
            ring = [
                [round(lon - half_lon, 6), round(lat - half_lat, 6)],
                [round(lon + half_lon, 6), round(lat - half_lat, 6)],
                [round(lon + half_lon, 6), round(lat + half_lat, 6)],
                [round(lon - half_lon, 6), round(lat + half_lat, 6)],
                [round(lon - half_lon, 6), round(lat - half_lat, 6)],
            ]
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        class_property: code,
                        "label": labels[code],
                        "source": dataset_id,
                    },
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                }
            )

    empty = [labels[c] for c in codes if not by_class[c]]
    fc = {"type": "FeatureCollection", "features": features}
    if empty:
        fc["warnings"] = [
            f"no homogeneous samples found for class(es): {empty} — the region may not "
            f"contain them; try a different area or larger region"
        ]
    return fc
