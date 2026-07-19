import numpy as np

from lulc_engine.classify.cross_val import mcnemars_test, pick_best, run_cv
from lulc_engine.config.schema import ClassifierConfig


def test_mcnemar_identical_predictions():
    y = np.array([0, 1, 0, 1, 0])
    preds = np.array([0, 1, 1, 1, 0])
    chi2_stat, p = mcnemars_test(y, preds, preds)
    assert chi2_stat == 0.0
    assert p == 1.0


def test_mcnemar_known_counts():
    # Construct: A correct/B wrong on 8 samples (b=8), A wrong/B correct on 2 (c=2)
    y = np.zeros(10, dtype=int)
    pred_a = np.array([0] * 8 + [1] * 2)
    pred_b = np.array([1] * 8 + [0] * 2)
    chi2_stat, p = mcnemars_test(y, pred_a, pred_b)
    # (|8-2|-1)^2 / (8+2) = 25/10 = 2.5
    assert chi2_stat == 2.5
    assert 0 < p < 1


def _synthetic(n_groups=24, per_group=12, seed=0):
    """Separable 2-class data with polygon-like groups."""
    rng = np.random.default_rng(seed)
    X, y, groups = [], [], []
    for g in range(n_groups):
        cls = g % 2
        center = np.array([2.5 * cls, -2.5 * cls])
        X.append(center + rng.normal(scale=0.7, size=(per_group, 2)))
        y.extend([cls] * per_group)
        groups.extend([g] * per_group)
    return np.vstack(X), np.array(y), np.array(groups)


def _fast_cfg():
    return ClassifierConfig(
        candidates=["RF", "SVM"],
        rf={"trees": 25, "bag_fraction": 0.9, "seed": 42},
        cv={"folds": 3, "seed": 42},
    )


def test_run_cv_structure_and_accuracy():
    X, y, groups = _synthetic()
    classes = {0: "A", 1: "B"}
    results = run_cv(X, y, groups, classes, _fast_cfg(), log=lambda *_: None)

    assert set(results) == {"RF", "SVM"}
    for r in results.values():
        assert 0.9 <= r["mean_accuracy"] <= 1.0  # data is separable
        assert len(r["confusion_matrix"]) == 2
        assert set(r["per_class"]) == {"A", "B"}
        assert (r["oof_predictions"] != -1).all()  # every sample predicted out-of-fold


def test_pick_best_returns_mcnemar():
    X, y, groups = _synthetic()
    results = run_cv(X, y, groups, {0: "A", 1: "B"}, _fast_cfg(), log=lambda *_: None)
    best, extra = pick_best(results, y, log=lambda *_: None)
    assert best in results
    assert extra["mcnemar"] is not None
    assert set(extra["mcnemar"]) == {"pair", "chi2", "p_value"}


def test_groups_never_split_across_folds():
    from sklearn.model_selection import StratifiedGroupKFold

    X, y, groups = _synthetic()
    skf = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)
    for train_idx, val_idx in skf.split(X, y, groups):
        assert set(groups[train_idx]).isdisjoint(set(groups[val_idx]))
