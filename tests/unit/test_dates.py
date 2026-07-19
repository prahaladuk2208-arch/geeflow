from lulc_engine.config.schema import Season
from lulc_engine.utils.dates import season_date_range


def test_simple_range():
    s = Season(name="dry", months=(1, 3))
    assert season_date_range(2020, s) == ("2020-01-01", "2020-03-31")


def test_end_of_february_leap_aware():
    s = Season(name="jf", months=(1, 2))
    assert season_date_range(2020, s) == ("2020-01-01", "2020-02-29")
    assert season_date_range(2021, s) == ("2021-01-01", "2021-02-28")


def test_wrapping_season_crosses_year():
    s = Season(name="ndjf", months=(11, 2))
    assert season_date_range(2019, s) == ("2019-11-01", "2020-02-29")


def test_offset_year():
    s = Season(name="dry", months=(1, 3))
    assert season_date_range(2020, s, offset_yr=-1) == ("2019-01-01", "2019-03-31")
    assert season_date_range(2020, s, offset_yr=2) == ("2022-01-01", "2022-03-31")


def test_thirty_day_month_end():
    s = Season(name="mon", months=(8, 9))
    assert season_date_range(2016, s) == ("2016-08-01", "2016-09-30")
