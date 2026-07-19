import os

import pytest

from lulc_engine.config import ConfigError, load_config
from lulc_engine.config.schema import AOIConfig, LulcConfig


def _base(**overrides):
    data = {
        "aoi": {"center_buffer": {"lat": 0.0, "lon": 0.0, "radius_m": 1000}},
        "classes": {0: "A", 1: "B"},
    }
    data.update(overrides)
    return data


def test_minimal_config_defaults(minimal_config):
    cfg = minimal_config
    assert cfg.project.name == "test-project"
    assert cfg.composite.reducer == "median"
    assert cfg.classifier.cv.folds == 5
    assert cfg.analysis.correlation_threshold == 0.5
    assert [e.name for e in cfg.sensor_eras] == ["mss", "tm", "s2"]
    # single default season
    assert [s.name for s in cfg.seasons] == ["annual"]


def test_time_points_sorted(minimal_config):
    assert minimal_config.time_points == [1980, 2005, 2020]


def test_era_boundaries(minimal_config):
    cfg = minimal_config
    assert cfg.era_for_year(1983).name == "mss"
    assert cfg.era_for_year(1984).name == "tm"
    assert cfg.era_for_year(2013).name == "tm"
    assert cfg.era_for_year(2014).name == "s2"
    assert cfg.scale_for_year(1975) == 60
    assert cfg.scale_for_year(2000) == 30
    assert cfg.scale_for_year(2022) == 10


def test_aoi_exactly_one_required():
    with pytest.raises(ValueError, match="exactly one"):
        AOIConfig()
    with pytest.raises(ValueError, match="exactly one"):
        AOIConfig(
            center_buffer={"lat": 0, "lon": 0, "radius_m": 1},
            ee_asset="projects/x/assets/y",
        )


def test_unknown_index_rejected():
    with pytest.raises(ValueError, match="unknown indices"):
        LulcConfig(**_base(features={"indices": ["NDVI", "BOGUS"]}))


def test_even_kernel_rejected():
    with pytest.raises(ValueError, match="odd"):
        LulcConfig(**_base(postprocess={"majority_filter": {"kernel": 4}}))


def test_single_class_rejected():
    with pytest.raises(ValueError, match="at least 2"):
        LulcConfig(**_base(classes={0: "Only"}))


def test_bad_reference_season_rejected():
    with pytest.raises(ValueError, match="reference_season"):
        LulcConfig(
            **_base(
                seasons=[{"name": "dry", "months": [1, 3]}],
                features={"seasonal": {"reference_season": "wet"}},
            )
        )


def test_env_var_expansion(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_GEE_PROJECT", "expanded-project")
    cfg_path = tmp_path / "lulc.yaml"
    cfg_path.write_text(
        """
project: { gee_project_id: "${MY_GEE_PROJECT}" }
aoi: { center_buffer: { lat: 0, lon: 0, radius_m: 100 } }
classes: { 0: A, 1: B }
""",
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    assert cfg.project.gee_project_id == "expanded-project"


def test_undefined_env_var_raises(tmp_path):
    assert "DEFINITELY_NOT_SET_XYZ" not in os.environ
    cfg_path = tmp_path / "lulc.yaml"
    cfg_path.write_text(
        """
project: { gee_project_id: "${DEFINITELY_NOT_SET_XYZ}" }
aoi: { center_buffer: { lat: 0, lon: 0, radius_m: 100 } }
classes: { 0: A, 1: B }
""",
        encoding="utf-8",
    )
    with pytest.raises(KeyError):
        load_config(cfg_path)


def test_missing_file_raises():
    with pytest.raises(ConfigError, match="not found"):
        load_config("no/such/lulc.yaml")


def test_validation_error_names_field(tmp_path):
    cfg_path = tmp_path / "lulc.yaml"
    cfg_path.write_text(
        """
aoi: { center_buffer: { lat: 95, lon: 0, radius_m: 100 } }
classes: { 0: A, 1: B }
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="center_buffer.lat"):
        load_config(cfg_path)


def test_resolve_path_relative_to_config(minimal_config, tmp_path):
    p = minimal_config.resolve_path("training/training_{year}.geojson", 2020)
    assert p == tmp_path / "training" / "training_2020.geojson"


def test_example_configs_load(forest_example_config, historical_example_config):
    assert len(forest_example_config.classes) == 4
    assert forest_example_config.reference_season.name == "dry"
    assert historical_example_config.era_for_year(1978).name == "mss"
    assert historical_example_config.era_for_year(1978).merge_sensors is True
