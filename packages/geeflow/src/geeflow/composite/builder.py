"""Seasonal composite creation with automatic scene-count fallbacks.

Fallback ladder (per season):
  1. primary sensor over the season window
  2. if fewer than min_scenes: merge the backup sensor (when one exists)
  3. if still short: expand the window by the era's search_window_yr on the primary sensor

Eras flagged merge_sensors (sparse archives like Landsat MSS) instead merge every
candidate sensor up-front, and always_expand widens the window unconditionally.
"""

from __future__ import annotations

from geeflow.dates import season_date_range
from geeflow.sensors.harmonize import get_collection, harmonized_bands_for
from geeflow.sensors.registry import get_sensors_for_year
from geeflow.specs import CompositeSpec, Season, SensorEra, era_for_year


def sensors_for(year: int, era: SensorEra) -> list[str]:
    """Sensor keys for a year: the era's explicit list if set, else the default mapping."""
    return era.sensors if era.sensors else get_sensors_for_year(year)


def _season_collection(
    sensor_keys: list[str], aoi, year: int, season: Season, offset_yr: int = 0
):
    start, end = season_date_range(year, season, offset_yr)
    col = get_collection(sensor_keys[0], aoi, start, end)
    for sk in sensor_keys[1:]:
        col = col.merge(get_collection(sk, aoi, start, end))
    return col


def build_season_collection(
    year: int,
    aoi,
    season: Season,
    era: SensorEra,
    min_scenes: int = 3,
    log=print,
):
    """One season's cloud-masked, harmonized collection after the fallback ladder.

    Returns (collection, primary_sensor_key, scene_count).
    """
    sensors = sensors_for(year, era)
    primary = sensors[0]

    if era.merge_sensors:
        col = _season_collection(sensors, aoi, year, season)
        if era.always_expand and era.search_window_yr > 0:
            log(f"    [{season.name}] expanding to +/- {era.search_window_yr} yr ({era.name} era)")
            for offset in range(-era.search_window_yr, era.search_window_yr + 1):
                if offset == 0:
                    continue
                col = col.merge(_season_collection(sensors, aoi, year, season, offset))
        count = col.size().getInfo()
        log(f"    [{season.name}] {count} scenes (merged {len(sensors)} sensors)")
        return col, primary, count

    col = _season_collection([primary], aoi, year, season)
    count = col.size().getInfo()
    log(f"    [{season.name}] {count} scenes from {primary}")

    if count < min_scenes and len(sensors) > 1:
        backup = sensors[1]
        log(f"    [{season.name}] <{min_scenes} scenes, merging backup sensor {backup}")
        col = col.merge(_season_collection([backup], aoi, year, season))
        count = col.size().getInfo()
        log(f"    [{season.name}] {count} scenes after backup merge")

    if count < min_scenes and era.search_window_yr > 0:
        log(f"    [{season.name}] still <{min_scenes}, expanding to +/- {era.search_window_yr} yr")
        for offset in range(-era.search_window_yr, era.search_window_yr + 1):
            if offset == 0:
                continue
            col = col.merge(_season_collection([primary], aoi, year, season, offset))
        count = col.size().getInfo()
        log(f"    [{season.name}] {count} scenes after expansion")

    return col, primary, count


def build_composites(
    year: int,
    aoi,
    seasons: list[Season],
    eras: list[SensorEra] | None = None,
    spec: CompositeSpec | None = None,
    log=print,
):
    """Per-season reduced composites for a year.

    Returns (composites, primary_sensor_key, band_names) where composites maps
    season name -> clipped ee.Image of harmonized spectral bands.
    """
    spec = spec or CompositeSpec()
    era = era_for_year(year, eras)
    primary = sensors_for(year, era)[0]
    band_names = harmonized_bands_for(primary)

    log(f"\nBuilding {len(seasons)}-season composites for {year} "
        f"(era={era.name}, sensor={primary}, scale={era.scale_m}m)")

    composites = {}
    for season in seasons:
        col, _, count = build_season_collection(
            year, aoi, season, era, min_scenes=spec.min_scenes, log=log
        )
        if count == 0:
            raise RuntimeError(
                f"No scenes found for {year} season {season.name!r} even after fallbacks. "
                f"Check scene availability and consider widening the season or search window."
            )
        reduced = col.median() if spec.reducer == "median" else col.mean()
        composites[season.name] = reduced.clip(aoi)

    return composites, primary, band_names
