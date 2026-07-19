"""High-level pipeline: config in, composites/features/analysis/classification out.

This is the Python API the CLI wraps; use it directly in notebooks:

    from lulc_engine import load_config, Pipeline
    pipe = Pipeline(load_config("lulc.yaml"))
    pipe.classify(2022)
"""

from __future__ import annotations

from lulc_engine.classify.analysis import load_selected_features, run_feature_analysis
from lulc_engine.classify.cross_val import pick_best, run_cv
from lulc_engine.classify.extract import extract_features, feature_columns
from lulc_engine.classify.postprocess import apply_postprocessing
from lulc_engine.classify.train import train_and_classify
from lulc_engine.composite.builder import build_composites, sensors_for
from lulc_engine.config.schema import LulcConfig
from lulc_engine.export.gee_export import export_classification
from lulc_engine.export.reports import write_classification_report
from lulc_engine.features.indices import add_indices
from lulc_engine.features.seasonal import compute_seasonal_features
from lulc_engine.features.texture import add_texture
from lulc_engine.labels.loaders import load_training
from lulc_engine.sensors.harmonize import get_collection
from lulc_engine.utils.dates import season_date_range
from lulc_engine.utils.ee_session import init_ee
from lulc_engine.utils.geometry import resolve_aoi


class Pipeline:
    def __init__(self, cfg: LulcConfig, initialize: bool = True, log=print):
        if cfg.project.backend != "gee":
            raise NotImplementedError(
                f"backend {cfg.project.backend!r} is not available yet; use 'gee'"
            )
        self.cfg = cfg
        self.log = log
        self._aoi = None
        if initialize:
            init_ee(cfg.project.gee_project_id)

    @property
    def aoi(self):
        if self._aoi is None:
            self._aoi = resolve_aoi(self.cfg.aoi, self.cfg.base_dir)
        return self._aoi

    # ------------------------------------------------------------------ steps

    def check(self, years: list[int] | None = None) -> dict:
        """Scene availability per year / season / sensor. Returns nested counts."""
        cfg = self.cfg
        years = years or cfg.time_points
        report: dict = {}
        for year in years:
            era = cfg.era_for_year(year)
            sensors = sensors_for(year, era)
            report[year] = {}
            self.log(f"\n{year} (era={era.name}, scale={era.scale_m}m):")
            for season in cfg.seasons:
                start, end = season_date_range(year, season)
                report[year][season.name] = {}
                for sk in sensors:
                    count = get_collection(sk, self.aoi, start, end).size().getInfo()
                    report[year][season.name][sk] = count
                    marker = "" if count >= cfg.composite.min_scenes else "  <-- LOW"
                    self.log(f"  {season.name:12s} {sk:18s} {count:4d} scenes{marker}")
        return report

    def build_composites(self, year: int):
        """Raw per-season spectral composites (no features yet)."""
        return build_composites(year, self.aoi, self.cfg, log=self.log)

    def build_features(self, year: int):
        """The full candidate feature stack for a year (ALL features, unpruned)."""
        cfg = self.cfg
        era = cfg.era_for_year(year)
        composites, sensor_key, band_names = self.build_composites(year)

        computed: dict[str, list[str]] = {}
        with_indices = {}
        for season_name, image in composites.items():
            image, names = add_indices(image, cfg.features.indices, band_names)
            with_indices[season_name] = image
            computed[season_name] = names

        ref_name = cfg.reference_season.name
        if era.name not in cfg.features.texture.exclude_eras:
            with_indices[ref_name], texture_names = add_texture(
                with_indices[ref_name], cfg.features.texture, band_names
            )
        else:
            texture_names = []

        stack = compute_seasonal_features(with_indices, computed, cfg)

        self.log(
            f"Feature stack {year}: spectral={band_names} indices={computed[ref_name]} "
            f"texture={texture_names} (+cross-season deltas/ratios/values)"
        )
        return stack

    def analyze(self, year: int) -> dict:
        """Correlation/VIF/importance reports for a year. Never prunes."""
        stack = self.build_features(year)
        training_fc, _ = load_training(self.cfg, year, log=self.log)
        df = extract_features(stack, training_fc, self.cfg, year, log=self.log)
        return run_feature_analysis(df, self.cfg, year, log=self.log)

    def classify(self, year: int, export: bool = True) -> dict:
        """CV model comparison -> best model -> GEE classification -> postprocess -> export."""
        cfg = self.cfg
        log = self.log

        stack = self.build_features(year)
        training_fc, _ = load_training(cfg, year, log=log)
        df = extract_features(stack, training_fc, cfg, year, log=log)

        selected = load_selected_features(cfg, year, log=log)
        feature_cols = selected if selected else feature_columns(df, cfg)

        X = df[feature_cols].fillna(0).values
        y = df[cfg.training.class_property].values.astype(int)
        groups = df[cfg.training.group_property].values

        import numpy as np

        n_groups = len(np.unique(groups))
        log(f"\nTraining pixels: {len(y)} from {n_groups} polygons")
        for code, name in cfg.sorted_class_items():
            log(f"  class {code} ({name}): {int(np.sum(y == code))} pixels")

        log("\n" + "=" * 60)
        log(f"STRATIFIED {cfg.classifier.cv.folds}-FOLD CV (polygon-grouped)")
        log("=" * 60)
        results = run_cv(X, y, groups, cfg.classes, cfg.classifier, log=log)

        best_name, extra = pick_best(results, y, log=log)
        best = results[best_name]
        log("\n" + "=" * 60)
        log(f"BEST CLASSIFIER: {best_name}")
        log(f"  OA = {best['mean_accuracy']:.4f} +/- {best['std_accuracy']:.4f}")
        log(f"  Kappa = {best['mean_kappa']:.4f} +/- {best['std_kappa']:.4f}")
        log("=" * 60)

        log(f"\nRetraining {best_name} on all {len(y)} pixels in Earth Engine...")
        classified = train_and_classify(stack, training_fc, feature_cols, best_name, cfg, year, log=log)
        classified = apply_postprocessing(classified, cfg, year, log=log)

        task = None
        if export:
            task = export_classification(classified, self.aoi, cfg, year, best_name, log=log)

        report_path = write_classification_report(
            cfg, year, feature_cols, y, results, best_name, extra["mcnemar"], log=log
        )

        return {
            "year": year,
            "best_classifier": best_name,
            "results": results,
            "classified": classified,
            "export_task": task,
            "report_path": report_path,
        }

    def run(self, years: list[int] | None = None, export: bool = True) -> dict:
        """Classify every configured time point."""
        years = years or self.cfg.time_points
        outcomes = {}
        for year in years:
            self.log(f"\n{'#' * 70}\n# {year}\n{'#' * 70}")
            outcomes[year] = self.classify(year, export=export)
        return outcomes
