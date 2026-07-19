"""Sample the feature stack at training locations into a pandas DataFrame."""

from __future__ import annotations

import pandas as pd

from lulc_engine.config.schema import LulcConfig


def extract_features(feature_stack, training_fc, cfg: LulcConfig, year: int, log=print) -> pd.DataFrame:
    """sampleRegions over the training collection -> per-pixel DataFrame.

    Columns: every band of the stack plus the class and group properties.
    """
    tc = cfg.training
    sampled = feature_stack.sampleRegions(
        collection=training_fc,
        properties=[tc.class_property, tc.group_property],
        scale=cfg.scale_for_year(year),
        geometries=False,
    )

    data = sampled.getInfo()
    rows = [feat["properties"] for feat in data["features"]]
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(
            "sampleRegions returned no pixels — check that training geometries overlap "
            "the AOI and that composites are not fully masked."
        )
    n_bands = len(df.columns) - 2  # minus class + group columns
    log(f"Extracted {len(df)} training pixels x {n_bands} features")
    return df


def feature_columns(df: pd.DataFrame, cfg: LulcConfig) -> list[str]:
    tc = cfg.training
    return [c for c in df.columns if c not in (tc.class_property, tc.group_property)]
