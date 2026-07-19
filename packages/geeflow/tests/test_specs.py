import pytest

from geeflow.specs import (
    CompositeSpec,
    Season,
    SeasonalSpec,
    TextureSpec,
    default_sensor_eras,
    era_for_year,
)


def test_default_eras():
    eras = default_sensor_eras()
    assert [e.name for e in eras] == ["mss", "tm", "s2"]
    assert eras[0].merge_sensors and eras[0].always_expand


def test_era_for_year_boundaries():
    assert era_for_year(1983).name == "mss"
    assert era_for_year(1984).name == "tm"
    assert era_for_year(2013).name == "tm"
    assert era_for_year(2014).name == "s2"
    assert era_for_year(1975).scale_m == 60
    assert era_for_year(2000).scale_m == 30
    assert era_for_year(2022).scale_m == 10


def test_era_for_year_unsorted_input():
    eras = list(reversed(default_sensor_eras()))
    assert era_for_year(1990, eras).name == "tm"


def test_era_for_year_out_of_range():
    eras = [e for e in default_sensor_eras() if e.name != "s2"]
    with pytest.raises(ValueError, match="no sensor era"):
        era_for_year(2020, eras)


def test_season_month_validation():
    with pytest.raises(ValueError):
        Season(name="bad", months=(0, 3))
    assert Season(name="wrap", months=(11, 2)).months == (11, 2)


def test_texture_spec_validation():
    with pytest.raises(ValueError, match="odd"):
        TextureSpec(window=4)
    with pytest.raises(ValueError, match="unknown texture metrics"):
        TextureSpec(metrics=["bogus"])


def test_defaults_sensible():
    assert CompositeSpec().reducer == "median"
    assert SeasonalSpec().deltas is True
