"""Typed specifications shared by all geeflow operations.

These are plain pydantic models with sensible defaults; downstream packages (e.g.
lulc-engine) embed them directly in their own configuration schemas.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SensorEra(BaseModel):
    """A year range mapped to a sensor family and working resolution.

    Eras are matched in ascending max_year order: the first era whose
    max_year >= year wins.
    """

    name: str
    max_year: int
    scale_m: int = Field(gt=0)
    search_window_yr: int = Field(default=1, ge=0)
    # merge_sensors: composite from ALL candidate sensors at once (sparse archives like MSS)
    merge_sensors: bool = False
    # always_expand: widen the date window by search_window_yr unconditionally, not just
    # when the scene count falls short
    always_expand: bool = False
    # Optional explicit sensor keys (see geeflow.sensors.registry.COLLECTIONS)
    sensors: list[str] | None = None


# Raw defaults: MSS era through 1983 at 60 m (sparse archive -> merged sensors, always
# widened window), TM/ETM+/OLI era through 2013 at 30 m, Sentinel-2 era afterwards at 10 m.
DEFAULT_SENSOR_ERAS: list[dict] = [
    {
        "name": "mss",
        "max_year": 1983,
        "scale_m": 60,
        "search_window_yr": 2,
        "merge_sensors": True,
        "always_expand": True,
    },
    {"name": "tm", "max_year": 2013, "scale_m": 30, "search_window_yr": 1},
    {"name": "s2", "max_year": 9999, "scale_m": 10, "search_window_yr": 1},
]


def default_sensor_eras() -> list[SensorEra]:
    return [SensorEra(**raw) for raw in DEFAULT_SENSOR_ERAS]


def era_for_year(year: int, eras: list[SensorEra] | None = None) -> SensorEra:
    eras = sorted(eras or default_sensor_eras(), key=lambda e: e.max_year)
    for era in eras:
        if year <= era.max_year:
            return era
    raise ValueError(f"no sensor era covers year {year} (max is {eras[-1].max_year})")


class Season(BaseModel):
    name: str
    months: tuple[int, int]  # (start_month, end_month) inclusive; start > end wraps the year

    @field_validator("months")
    @classmethod
    def _valid_months(cls, v):
        if not (1 <= v[0] <= 12 and 1 <= v[1] <= 12):
            raise ValueError(f"months must be within 1-12, got {v}")
        return v


class CompositeSpec(BaseModel):
    reducer: Literal["median", "mean"] = "median"
    min_scenes: int = Field(default=3, ge=1)


# Canonical spectral index registry: name -> required standard bands.
# The builders live in geeflow.features.indices; an index is only computed when all its
# required bands are present, which is how band-poor eras (e.g. MSS without Blue/SWIR)
# automatically get a reduced set.
KNOWN_INDICES: dict[str, list[str]] = {
    "NDVI": ["NIR", "Red"],
    "SAVI": ["NIR", "Red"],
    "EVI": ["NIR", "Red", "Blue"],
    "NDMI": ["NIR", "SWIR1"],
    "NBR": ["NIR", "SWIR2"],
    "BlueGreenNIR": ["Blue", "Green", "NIR"],
    "GreenRed": ["Green", "Red"],
    "NDRE": ["NIR", "RedEdge1"],
    "CIre": ["NIR", "RedEdge1"],
    "NDWI": ["Green", "NIR"],
    "NDBI": ["SWIR1", "NIR"],
}

KNOWN_TEXTURE_METRICS = {"entropy", "contrast", "variance", "correlation"}


class TextureSpec(BaseModel):
    enabled: bool = True
    band: str = "NIR"
    metrics: list[str] = ["entropy", "contrast"]
    window: int = 3
    # GLCM texture is rarely meaningful at very coarse scales; skip these eras
    exclude_eras: list[str] = ["mss"]

    @field_validator("metrics")
    @classmethod
    def _known_metrics(cls, v):
        unknown = set(v) - KNOWN_TEXTURE_METRICS
        if unknown:
            raise ValueError(
                f"unknown texture metrics {sorted(unknown)}; known: {sorted(KNOWN_TEXTURE_METRICS)}"
            )
        return v

    @field_validator("window")
    @classmethod
    def _odd_window(cls, v):
        if v < 3 or v % 2 == 0:
            raise ValueError("texture window must be an odd integer >= 3")
        return v


class SeasonalSpec(BaseModel):
    """Cross-season phenology features (computed against a reference season).

    For every non-reference season S and index X:
      deltas -> delta_X_S = X(S) - X(reference)
      ratios -> X_ratio_S = X(reference) / max(X(S), 0.001)
      season_values -> X_S = X(S)
    The *_indices lists restrict which indices participate; None means all computed indices.
    """

    deltas: bool = True
    ratios: bool = True
    season_values: bool = True
    delta_indices: list[str] | None = None
    ratio_indices: list[str] | None = None
    value_indices: list[str] | None = None
    reference_season: str | None = None  # default: first season in the seasons list
