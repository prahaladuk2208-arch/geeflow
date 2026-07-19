"""Polygon-grouped stratified cross-validation comparing RF / GBT / SVM.

Grouping by source polygon keeps pixels from one polygon inside a single fold, so
accuracy estimates are not inflated by spatial autocorrelation between neighbors.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import chi2
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.svm import SVC

from lulc_engine.config.schema import ClassifierConfig


def mcnemars_test(y_true, y_pred_a, y_pred_b) -> tuple[float, float]:
    """McNemar's test (with continuity correction) between two classifiers.

    Returns (chi2 statistic, p-value).
    """
    correct_a = y_pred_a == y_true
    correct_b = y_pred_b == y_true

    b = np.sum(correct_a & ~correct_b)
    c = np.sum(~correct_a & correct_b)

    if (b + c) == 0:
        return 0.0, 1.0

    chi2_stat = (abs(b - c) - 1) ** 2 / (b + c)
    p_value = 1 - chi2.cdf(chi2_stat, df=1)
    return float(chi2_stat), float(p_value)


def _make_classifiers(cfg: ClassifierConfig) -> dict:
    factories = {
        "RF": lambda: RandomForestClassifier(
            n_estimators=cfg.rf.trees,
            max_features="sqrt",
            max_samples=cfg.rf.bag_fraction,
            random_state=cfg.rf.seed,
            n_jobs=-1,
        ),
        "GBT": lambda: GradientBoostingClassifier(
            n_estimators=cfg.gbt.trees,
            random_state=cfg.gbt.seed,
        ),
        "SVM": lambda: SVC(
            kernel=cfg.svm.kernel.lower(),
            C=cfg.svm.cost,
            gamma=cfg.svm.gamma,
        ),
    }
    return {name: factories[name] for name in cfg.candidates}


def run_cv(X, y, groups, classes: dict[int, str], cfg: ClassifierConfig, log=print) -> dict:
    """Grouped stratified k-fold CV for every candidate classifier.

    Returns per-classifier: mean/std overall accuracy and Kappa, confusion matrix and
    per-class precision/recall/F1 from out-of-fold predictions, and the raw
    out-of-fold prediction vector (for McNemar's test).
    """
    skf = StratifiedGroupKFold(n_splits=cfg.cv.folds, shuffle=True, random_state=cfg.cv.seed)
    class_codes = sorted(classes.keys())
    class_names = [classes[k] for k in class_codes]

    results = {}
    for name, clf_factory in _make_classifiers(cfg).items():
        fold_accuracies = []
        fold_kappas = []
        fold_predictions = np.full(len(y), -1)

        log(f"\n  {name}:")
        for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y, groups)):
            clf = clf_factory()
            clf.fit(X[train_idx], y[train_idx])
            preds = clf.predict(X[val_idx])
            fold_predictions[val_idx] = preds

            acc = accuracy_score(y[val_idx], preds)
            kappa = cohen_kappa_score(y[val_idx], preds)
            fold_accuracies.append(acc)
            fold_kappas.append(kappa)
            log(f"    fold {fold_idx + 1}: OA = {acc:.3f}")

        cm = confusion_matrix(y, fold_predictions, labels=class_codes)
        report = classification_report(
            y,
            fold_predictions,
            labels=class_codes,
            target_names=class_names,
            output_dict=True,
            zero_division=0,
        )

        results[name] = {
            "mean_accuracy": float(np.mean(fold_accuracies)),
            "std_accuracy": float(np.std(fold_accuracies)),
            "mean_kappa": float(np.mean(fold_kappas)),
            "std_kappa": float(np.std(fold_kappas)),
            "confusion_matrix": cm.tolist(),
            "per_class": {
                cn: {
                    "precision": report[cn]["precision"],
                    "recall": report[cn]["recall"],
                    "f1": report[cn]["f1-score"],
                }
                for cn in class_names
                if cn in report
            },
            "oof_predictions": fold_predictions,
        }

        r = results[name]
        log(
            f"    OA = {r['mean_accuracy']:.4f} +/- {r['std_accuracy']:.4f} | "
            f"Kappa = {r['mean_kappa']:.4f} +/- {r['std_kappa']:.4f}"
        )

    return results


def pick_best(results: dict, y, log=print) -> tuple[str, dict]:
    """Best classifier by mean OA, with McNemar's test against the runner-up."""
    best_name = max(results, key=lambda k: results[k]["mean_accuracy"])
    ranked = sorted(results.items(), key=lambda kv: kv[1]["mean_accuracy"], reverse=True)

    mcnemar = None
    if len(ranked) >= 2:
        (name1, r1), (name2, r2) = ranked[0], ranked[1]
        chi2_stat, p_val = mcnemars_test(y, r1["oof_predictions"], r2["oof_predictions"])
        sig = "SIGNIFICANT" if p_val < 0.05 else "not significant"
        log(f"\nMcNemar's test: {name1} vs {name2}: chi2 = {chi2_stat:.3f}, p = {p_val:.4f} ({sig})")
        mcnemar = {"pair": [name1, name2], "chi2": chi2_stat, "p_value": p_val}

    return best_name, {"mcnemar": mcnemar}
