"""JSON accuracy reports."""

from __future__ import annotations

import json

import numpy as np

from lulc_engine.config.schema import LulcConfig


def write_classification_report(
    cfg: LulcConfig,
    year: int,
    feature_cols: list[str],
    y,
    cv_results: dict,
    best_name: str,
    mcnemar: dict | None,
    log=print,
):
    """Persist the run's accuracy report to output_dir/tables. Returns the path."""
    report = {
        "project": cfg.project.name,
        "year": year,
        "features_used": feature_cols,
        "n_features": len(feature_cols),
        "total_pixels": int(len(y)),
        "class_distribution": {
            int(code): {"name": name, "count": int(np.sum(y == code))}
            for code, name in cfg.sorted_class_items()
        },
        "cv_folds": cfg.classifier.cv.folds,
        "results": {
            name: {k: v for k, v in r.items() if k != "oof_predictions"}
            for name, r in cv_results.items()
        },
        "mcnemar": mcnemar,
        "best_classifier": best_name,
    }

    tables = cfg.resolve_path(cfg.output_dir) / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    path = tables / f"classification_report_{year}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    log(f"Report saved: {path}")
    return path
