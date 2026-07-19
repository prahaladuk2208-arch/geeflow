"""Opt-in smoke tests against the real Earth Engine API.

Run with:  LULC_GEE_TESTS=1 pytest -m gee
Requires cached credentials (`lulc auth`) and a GEE-enabled project in the
LULC_GEE_PROJECT environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.gee,
    pytest.mark.skipif(
        not os.environ.get("LULC_GEE_TESTS"),
        reason="set LULC_GEE_TESTS=1 (and LULC_GEE_PROJECT) to run real-GEE tests",
    ),
]

EXAMPLES = Path(__file__).parent.parent.parent / "examples"


@pytest.fixture(scope="module")
def pipeline():
    from lulc_engine.config import load_config
    from lulc_engine.pipeline import Pipeline

    cfg = load_config(EXAMPLES / "forest_monitoring" / "lulc.yaml")
    cfg.project.gee_project_id = os.environ["LULC_GEE_PROJECT"]
    return Pipeline(cfg)


def test_check_finds_scenes(pipeline):
    report = pipeline.check([2022])
    counts = [c for season in report[2022].values() for c in season.values()]
    assert any(c > 0 for c in counts)


def test_feature_stack_bands(pipeline):
    stack = pipeline.build_features(2022)
    bands = stack.bandNames().getInfo()
    # spectral + red-edge + indices + texture + cross-season features
    assert "NDVI" in bands
    assert "GLCM_entropy" in bands
    assert "delta_NDVI_wet" in bands
    assert len(bands) > 20


def test_classify_smoke(pipeline, tmp_path):
    pipeline.cfg.output_dir = str(tmp_path)
    result = pipeline.classify(2022, export=False)
    assert result["best_classifier"] in ("RF", "GBT", "SVM")
    best = result["results"][result["best_classifier"]]
    assert best["mean_accuracy"] > 0.6  # wiring test, not a science test
    assert result["report_path"].exists()
