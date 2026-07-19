import json

import pytest

from lulc_engine.labels.loaders import parse_training_file, summarize

VALID_FC = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"class": 0},
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        },
        {
            "type": "Feature",
            "properties": {"class": 0},
            "geometry": {"type": "Point", "coordinates": [0.5, 0.5]},
        },
        {
            "type": "Feature",
            "properties": {"class": 1},
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[[2, 2], [3, 2], [3, 3], [2, 2]]]],
            },
        },
        {
            "type": "Feature",
            "properties": {},  # missing class -> skipped with warning
            "geometry": {"type": "Polygon", "coordinates": [[[5, 5], [6, 5], [6, 6], [5, 5]]]},
        },
        {
            "type": "Feature",
            "properties": {"class": 1},
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},  # unsupported
        },
    ],
}


@pytest.fixture
def training_file(tmp_path):
    p = tmp_path / "training_2020.geojson"
    p.write_text(json.dumps(VALID_FC), encoding="utf-8")
    return p


def test_parse_skips_bad_features_with_warnings(training_file):
    parsed, warnings = parse_training_file(training_file, "class")
    assert len(parsed) == 3
    assert len(warnings) == 2
    assert any("missing 'class'" in w for w in warnings)
    assert any("LineString" in w for w in warnings)


def test_parse_keeps_geometry_types(training_file):
    parsed, _ = parse_training_file(training_file, "class")
    assert [f.geom_type for f in parsed] == ["Polygon", "Point", "MultiPolygon"]


def test_summarize_counts_and_warns_low(training_file, minimal_config):
    parsed, _ = parse_training_file(training_file, "class")
    summary = summarize(parsed, minimal_config, str(training_file))
    assert summary.class_counts == {0: 2, 1: 1}
    # default min_polygons_per_class = 5 -> both classes flagged low
    assert len(summary.warnings) == 2


def test_unknown_class_in_data_warns(tmp_path, minimal_config):
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"class": 7},
                "geometry": {"type": "Point", "coordinates": [0, 0]},
            }
        ],
    }
    p = tmp_path / "t.geojson"
    p.write_text(json.dumps(fc), encoding="utf-8")
    parsed, _ = parse_training_file(p, "class")
    summary = summarize(parsed, minimal_config, str(p))
    assert any("not in config" in w for w in summary.warnings)


def test_m2_formats_raise_not_implemented(tmp_path):
    shp = tmp_path / "training.shp"
    shp.write_bytes(b"")
    with pytest.raises(NotImplementedError, match="future release"):
        parse_training_file(shp, "class")


def test_unknown_extension_rejected(tmp_path):
    weird = tmp_path / "training.xyz"
    weird.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        parse_training_file(weird, "class")


def test_non_featurecollection_rejected(tmp_path):
    p = tmp_path / "t.geojson"
    p.write_text('{"type": "Feature"}', encoding="utf-8")
    with pytest.raises(ValueError, match="FeatureCollection"):
        parse_training_file(p, "class")
