import numpy as np
import pandas as pd

from lulc_engine.classify.analysis import compute_vif, load_selected_features


def test_vif_independent_features_near_one():
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "a": rng.normal(size=500),
            "b": rng.normal(size=500),
            "c": rng.normal(size=500),
        }
    )
    vif = compute_vif(df, ["a", "b", "c"])
    assert (vif["VIF"] < 1.1).all()


def test_vif_flags_linear_combination():
    rng = np.random.default_rng(42)
    a = rng.normal(size=500)
    b = rng.normal(size=500)
    df = pd.DataFrame({"a": a, "b": b, "combo": a + b + rng.normal(scale=0.01, size=500)})
    vif = compute_vif(df, ["a", "b", "combo"])
    assert vif.iloc[0]["VIF"] > 100  # the collinear trio dominates


def test_load_selected_features_absent_returns_none(minimal_config):
    assert load_selected_features(minimal_config, 2020, log=lambda *_: None) is None


def test_load_selected_features_reads_file(minimal_config):
    sel = minimal_config.base_dir / "selected_features_2020.json"
    sel.write_text('{"features": ["NDVI", "SAVI"]}', encoding="utf-8")
    assert load_selected_features(minimal_config, 2020, log=lambda *_: None) == ["NDVI", "SAVI"]
