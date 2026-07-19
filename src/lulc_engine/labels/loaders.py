"""Training-data loading.

M1 supports GeoJSON files and Earth Engine FeatureCollection assets (e.g. shared by a
partner organization). Shapefile/KML/GPX/CSV land in M2 via geopandas.

Every training feature gets a group id (config: training.group_property) so
cross-validation can be grouped by source polygon — pixels from one polygon never
appear in both a training and a validation fold.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from lulc_engine.config.schema import LulcConfig

_SUPPORTED_EXTENSIONS = {".geojson", ".json"}
_M2_EXTENSIONS = {".shp", ".kml", ".kmz", ".gpx", ".csv"}


@dataclass
class ParsedFeature:
    geom_type: str
    coordinates: list
    properties: dict


@dataclass
class TrainingSummary:
    source: str
    n_features: int
    class_counts: dict[int, int]
    warnings: list[str] = field(default_factory=list)


def parse_training_file(path: Path, class_property: str) -> tuple[list[ParsedFeature], list[str]]:
    """Parse a training vector file into plain-Python features (no Earth Engine).

    Returns (features, warnings). Features missing the class property or with
    unsupported geometry types are skipped with a warning.
    """
    ext = path.suffix.lower()
    if ext in _M2_EXTENSIONS:
        raise NotImplementedError(
            f"{ext} training files are planned for a future release; "
            f"convert to GeoJSON for now (e.g. with ogr2ogr or geopandas)."
        )
    if ext not in _SUPPORTED_EXTENSIONS:
        raise ValueError(f"unsupported training file type {ext!r}: {path}")

    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    if gj.get("type") != "FeatureCollection":
        raise ValueError(f"{path} is not a GeoJSON FeatureCollection")

    parsed: list[ParsedFeature] = []
    warnings: list[str] = []
    for i, feat in enumerate(gj.get("features", [])):
        props = dict(feat.get("properties") or {})
        if props.get(class_property) is None:
            warnings.append(f"feature {i} missing {class_property!r} property; skipped")
            continue
        geom = feat.get("geometry") or {}
        gtype = geom.get("type")
        if gtype not in ("Point", "Polygon", "MultiPolygon"):
            warnings.append(f"feature {i} has unsupported geometry {gtype!r}; skipped")
            continue
        parsed.append(ParsedFeature(gtype, geom["coordinates"], props))
    return parsed, warnings


def summarize(parsed: list[ParsedFeature], cfg: LulcConfig, source: str) -> TrainingSummary:
    """Class distribution + low-count warnings for parsed features."""
    cp = cfg.training.class_property
    counts: dict[int, int] = {}
    for f in parsed:
        cls = int(f.properties[cp])
        counts[cls] = counts.get(cls, 0) + 1

    warnings = []
    for code, name in cfg.sorted_class_items():
        n = counts.get(code, 0)
        if n < cfg.training.min_polygons_per_class:
            warnings.append(
                f"class {code} ({name}): only {n} polygons "
                f"(minimum recommended: {cfg.training.min_polygons_per_class})"
            )
    unknown = sorted(set(counts) - set(cfg.classes))
    if unknown:
        warnings.append(f"training data contains classes not in config: {unknown}")

    return TrainingSummary(source, len(parsed), counts, warnings)


def to_feature_collection(parsed: list[ParsedFeature], cfg: LulcConfig):
    """Build the ee.FeatureCollection, assigning a sequential group id per feature."""
    import ee

    gp = cfg.training.group_property
    ee_features = []
    for idx, f in enumerate(parsed):
        props = dict(f.properties)
        props[gp] = idx
        if f.geom_type == "Point":
            geom = ee.Geometry.Point(f.coordinates)
        elif f.geom_type == "Polygon":
            geom = ee.Geometry.Polygon(f.coordinates)
        else:
            geom = ee.Geometry.MultiPolygon(f.coordinates)
        ee_features.append(ee.Feature(geom, props))
    return ee.FeatureCollection(ee_features)


def load_training(cfg: LulcConfig, year: int, log=print):
    """Load the year's training data from file or EE asset per config.

    Returns (ee.FeatureCollection, TrainingSummary).
    """
    import ee

    tc = cfg.training
    if tc.ee_asset:
        asset_id = tc.ee_asset.format(year=year)
        log(f"Loading training data from EE asset: {asset_id}")
        fc = ee.FeatureCollection(asset_id)
        # system:index is unique per feature -> safe grouping key for spatial CV
        gp = tc.group_property
        fc = fc.map(lambda f: f.set(gp, f.get("system:index")))
        hist = fc.aggregate_histogram(tc.class_property).getInfo()
        counts = {int(float(k)): int(v) for k, v in hist.items()}
        n = sum(counts.values())
        summary = TrainingSummary(asset_id, n, counts)
        _report(summary, cfg, log)
        return fc, summary

    path = cfg.resolve_path(tc.path, year)
    if not path.exists():
        raise FileNotFoundError(
            f"training data not found: {path}\n"
            f"Generate a collector script with `lulc labels template --year {year}`, draw "
            f"polygons in the GEE Code Editor, and save the export to that path."
        )

    log(f"Loading training data from {path}")
    parsed, warnings = parse_training_file(path, tc.class_property)
    summary = summarize(parsed, cfg, str(path))
    summary.warnings = warnings + summary.warnings
    _report(summary, cfg, log)
    return to_feature_collection(parsed, cfg), summary


def _report(summary: TrainingSummary, cfg: LulcConfig, log) -> None:
    log(f"  {summary.n_features} training features")
    for code, name in cfg.sorted_class_items():
        log(f"    class {code} ({name}): {summary.class_counts.get(code, 0)}")
    for w in summary.warnings:
        log(f"  WARNING: {w}")
