"""Pydantic models for the lulc-engine project configuration (lulc.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from lulc_engine.config.defaults import (
    DEFAULT_SENSOR_ERAS,
    KNOWN_INDICES,
    KNOWN_TEXTURE_METRICS,
)


def _default_sensor_eras() -> list[SensorEra]:
    return [SensorEra(**raw) for raw in DEFAULT_SENSOR_ERAS]


class CenterBuffer(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_m: float = Field(gt=0)


class AOIConfig(BaseModel):
    """Area of interest. Exactly one of the three sources must be set."""

    center_buffer: CenterBuffer | None = None
    geojson: Path | None = None
    ee_asset: str | None = None

    @model_validator(mode="after")
    def _exactly_one(self):
        set_fields = [
            n for n in ("center_buffer", "geojson", "ee_asset") if getattr(self, n) is not None
        ]
        if len(set_fields) != 1:
            raise ValueError(
                f"aoi must set exactly one of center_buffer, geojson, ee_asset (got {set_fields or 'none'})"
            )
        return self


class SensorEra(BaseModel):
    """A year range mapped to a sensor family and working resolution.

    Eras are matched in order: the first era whose max_year >= year wins.
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
    # Optional explicit sensor keys (see sensors.registry.COLLECTIONS); default resolved by year
    sensors: list[str] | None = None


class Season(BaseModel):
    name: str
    months: tuple[int, int]  # (start_month, end_month) inclusive; start > end wraps the year

    @field_validator("months")
    @classmethod
    def _valid_months(cls, v):
        if not (1 <= v[0] <= 12 and 1 <= v[1] <= 12):
            raise ValueError(f"months must be within 1-12, got {v}")
        return v


class TextureConfig(BaseModel):
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
            raise ValueError(f"unknown texture metrics {sorted(unknown)}; known: {sorted(KNOWN_TEXTURE_METRICS)}")
        return v

    @field_validator("window")
    @classmethod
    def _odd_window(cls, v):
        if v < 3 or v % 2 == 0:
            raise ValueError("texture window must be an odd integer >= 3")
        return v


class SeasonalFeatureConfig(BaseModel):
    """Cross-season phenology features (computed against a reference season).

    For every non-reference season S and index X:
      deltas -> delta_X_S = X(S) - X(reference)
      ratios -> X_ratio_S = X(reference) / max(X(S), 0.001)
      season_values -> X_S = X(S)
    The *_indices lists restrict which indices participate; None means all configured indices.
    """

    deltas: bool = True
    ratios: bool = True
    season_values: bool = True
    delta_indices: list[str] | None = None
    ratio_indices: list[str] | None = None
    value_indices: list[str] | None = None
    reference_season: str | None = None  # default: first season in `seasons`


class FeaturesConfig(BaseModel):
    indices: list[str] = ["NDVI", "SAVI", "EVI", "NDMI", "NBR", "BlueGreenNIR", "GreenRed"]
    texture: TextureConfig = TextureConfig()
    seasonal: SeasonalFeatureConfig = SeasonalFeatureConfig()

    @field_validator("indices")
    @classmethod
    def _known_indices(cls, v):
        unknown = set(v) - set(KNOWN_INDICES)
        if unknown:
            raise ValueError(f"unknown indices {sorted(unknown)}; known: {sorted(KNOWN_INDICES)}")
        return v


class CompositeConfig(BaseModel):
    reducer: Literal["median", "mean"] = "median"
    min_scenes: int = Field(default=3, ge=1)


class TrainingConfig(BaseModel):
    source: Literal["user", "public_consensus", "mixed"] = "user"
    # Path template relative to the config file; {year} is substituted
    path: str = "training/training_{year}.geojson"
    # Alternatively an Earth Engine FeatureCollection asset id (may contain {year})
    ee_asset: str | None = None
    class_property: str = "class"
    group_property: str = "polygon_id"
    min_polygons_per_class: int = Field(default=5, ge=1)


class RFParams(BaseModel):
    trees: int = 800
    bag_fraction: float = Field(default=0.9, gt=0, le=1)
    seed: int = 42


class GBTParams(BaseModel):
    trees: int = 500
    seed: int = 42


class SVMParams(BaseModel):
    kernel: Literal["RBF", "LINEAR", "POLY", "SIGMOID"] = "RBF"
    cost: float = 10.0
    gamma: float = 0.1


class CVConfig(BaseModel):
    folds: int = Field(default=5, ge=2)
    seed: int = 42


class ClassifierConfig(BaseModel):
    candidates: list[Literal["RF", "GBT", "SVM"]] = ["RF", "GBT", "SVM"]
    rf: RFParams = RFParams()
    gbt: GBTParams = GBTParams()
    svm: SVMParams = SVMParams()
    cv: CVConfig = CVConfig()
    # Optional user-authored pruned feature list ({"features": [...]}). Template relative
    # to the config file; if the file does not exist, ALL features are used.
    feature_selection: str = "selected_features_{year}.json"

    @field_validator("candidates")
    @classmethod
    def _non_empty(cls, v):
        if not v:
            raise ValueError("classifier.candidates must not be empty")
        return v


class AnalysisConfig(BaseModel):
    correlation_threshold: float = Field(default=0.5, gt=0, lt=1)
    vif_threshold: float = Field(default=10.0, gt=0)


class MajorityFilterConfig(BaseModel):
    enabled: bool = True
    kernel: int = 3
    iterations: int = Field(default=1, ge=1)

    @field_validator("kernel")
    @classmethod
    def _odd_kernel(cls, v):
        if v < 3 or v % 2 == 0:
            raise ValueError("majority filter kernel must be an odd integer >= 3")
        return v


class PostprocessConfig(BaseModel):
    majority_filter: MajorityFilterConfig = MajorityFilterConfig()
    min_mapping_unit_ha: float | None = None


class ExportConfig(BaseModel):
    target: Literal["drive", "asset"] = "drive"
    folder: str = "LULC_Outputs"
    prefix: str = "classified"
    crs: str = "EPSG:4326"
    scale_m: int | None = None  # None = the era's native scale
    asset_root: str | None = None  # required when target == "asset"
    max_pixels: float = 1e10

    @model_validator(mode="after")
    def _asset_root_required(self):
        if self.target == "asset" and not self.asset_root:
            raise ValueError("export.asset_root is required when export.target is 'asset'")
        return self


class ProjectConfig(BaseModel):
    name: str = "my-lulc-project"
    gee_project_id: str | None = None
    backend: Literal["gee", "local"] = "gee"


class LulcConfig(BaseModel):
    """Root configuration for a lulc-engine project."""

    project: ProjectConfig = ProjectConfig()
    aoi: AOIConfig
    time_points: list[int] = Field(default_factory=list)
    sensor_eras: list[SensorEra] = Field(default_factory=_default_sensor_eras)
    seasons: list[Season] = Field(default_factory=lambda: [Season(name="annual", months=(1, 12))])
    composite: CompositeConfig = CompositeConfig()
    features: FeaturesConfig = FeaturesConfig()
    classes: dict[int, str]
    training: TrainingConfig = TrainingConfig()
    classifier: ClassifierConfig = ClassifierConfig()
    analysis: AnalysisConfig = AnalysisConfig()
    postprocess: PostprocessConfig = PostprocessConfig()
    export: ExportConfig = ExportConfig()
    output_dir: str = "outputs"

    # Set by the loader to the config file's directory; relative paths resolve against it.
    base_dir: Path = Path(".")

    @field_validator("time_points")
    @classmethod
    def _valid_years(cls, v):
        bad = [y for y in v if not (1972 <= y <= 2100)]
        if bad:
            raise ValueError(f"time_points outside 1972-2100: {bad}")
        return sorted(v)

    @field_validator("classes")
    @classmethod
    def _enough_classes(cls, v):
        if len(v) < 2:
            raise ValueError("classes must define at least 2 classes")
        return v

    @field_validator("seasons")
    @classmethod
    def _unique_seasons(cls, v):
        if not v:
            raise ValueError("at least one season is required")
        names = [s.name for s in v]
        if len(set(names)) != len(names):
            raise ValueError(f"season names must be unique, got {names}")
        return v

    @field_validator("sensor_eras")
    @classmethod
    def _sorted_eras(cls, v):
        if not v:
            raise ValueError("at least one sensor era is required")
        return sorted(v, key=lambda e: e.max_year)

    @model_validator(mode="after")
    def _cross_checks(self):
        ref = self.features.seasonal.reference_season
        season_names = [s.name for s in self.seasons]
        if ref is not None and ref not in season_names:
            raise ValueError(f"seasonal.reference_season {ref!r} not in seasons {season_names}")
        texture_eras = set(self.features.texture.exclude_eras)
        era_names = {e.name for e in self.sensor_eras}
        unknown = texture_eras - era_names
        if unknown:
            raise ValueError(f"texture.exclude_eras references unknown eras {sorted(unknown)}")
        return self

    # ------------------------------------------------------------------ helpers

    def era_for_year(self, year: int) -> SensorEra:
        for era in self.sensor_eras:  # sorted by max_year
            if year <= era.max_year:
                return era
        raise ValueError(f"no sensor era covers year {year} (max is {self.sensor_eras[-1].max_year})")

    def scale_for_year(self, year: int) -> int:
        return self.era_for_year(year).scale_m

    @property
    def reference_season(self) -> Season:
        ref = self.features.seasonal.reference_season
        if ref is None:
            return self.seasons[0]
        return next(s for s in self.seasons if s.name == ref)

    def resolve_path(self, template: str, year: int | None = None) -> Path:
        """Resolve a path template (may contain {year}) against the config directory."""
        p = template.format(year=year) if year is not None else template
        path = Path(p)
        return path if path.is_absolute() else (self.base_dir / path)

    def sorted_class_items(self) -> list[tuple[int, str]]:
        return sorted(self.classes.items())
