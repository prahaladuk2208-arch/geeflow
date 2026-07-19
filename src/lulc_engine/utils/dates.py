"""Season/date helpers (pure Python, no Earth Engine)."""

from __future__ import annotations

import calendar

from lulc_engine.config.schema import Season


def season_date_range(year: int, season: Season, offset_yr: int = 0) -> tuple[str, str]:
    """ISO (start, end) dates for a season anchored to `year` (+ optional year offset).

    Seasons whose start month is after their end month (e.g. Nov-Feb) wrap into the
    following calendar year. The end day is the true last day of the end month.
    """
    start_month, end_month = season.months
    start_year = year + offset_yr
    end_year = start_year if start_month <= end_month else start_year + 1
    end_day = calendar.monthrange(end_year, end_month)[1]
    return (
        f"{start_year}-{start_month:02d}-01",
        f"{end_year}-{end_month:02d}-{end_day:02d}",
    )
