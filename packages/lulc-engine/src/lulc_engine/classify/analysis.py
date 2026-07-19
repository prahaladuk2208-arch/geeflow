"""Collinearity + importance analysis. Reports only — NEVER auto-prunes.

The philosophy: compute every candidate feature first, look at the evidence
(correlation structure, VIF, preliminary importance), then let the analyst write the
pruned feature list. `lulc classify` picks that list up if present.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lulc_engine.classify.extract import feature_columns
from lulc_engine.config.schema import LulcConfig


def compute_vif(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Variance Inflation Factor per feature (least-squares on standardized values)."""
    from numpy.linalg import LinAlgError, lstsq

    X = df[feature_cols].values.astype(float)
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-10)

    vif_data = []
    for i, col in enumerate(feature_cols):
        try:
            others = np.delete(X, i, axis=1)
            coeffs, _, _, _ = lstsq(others, X[:, i], rcond=None)
            predicted = others @ coeffs
            ss_res = np.sum((X[:, i] - predicted) ** 2)
            ss_tot = np.sum((X[:, i] - X[:, i].mean()) ** 2)
            r_squared = 1 - (ss_res / (ss_tot + 1e-10))
            vif = 1 / (1 - r_squared + 1e-10)
        except (LinAlgError, ValueError):
            vif = float("inf")
        vif_data.append({"Feature": col, "VIF": vif})

    return pd.DataFrame(vif_data).sort_values("VIF", ascending=False)


def _plot_correlation_heatmap(corr: pd.DataFrame, title: str, path: Path) -> None:
    n = len(corr)
    fig, ax = plt.subplots(figsize=(max(8, n * 0.5), max(7, n * 0.45)))
    masked = np.where(np.triu(np.ones_like(corr, dtype=bool)), np.nan, corr.values)
    im = ax.imshow(masked, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n), corr.columns, rotation=90, fontsize=7)
    ax.set_yticks(range(n), corr.index, fontsize=7)
    if n <= 30:
        for i in range(n):
            for j in range(i):
                ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run_feature_analysis(df: pd.DataFrame, cfg: LulcConfig, year: int, log=print) -> dict:
    """Correlation matrix + VIF + preliminary RF importance, written to output_dir.

    Returns a dict of the produced artifact paths and dataframes.
    """
    from sklearn.ensemble import RandomForestClassifier

    feature_cols = feature_columns(df, cfg)
    log(f"\nAnalyzing {len(feature_cols)} candidate features...")

    out_dir = cfg.resolve_path(cfg.output_dir)
    figures = out_dir / "figures"
    tables = out_dir / "tables"
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    # --- Correlation ---
    corr = df[feature_cols].corr()
    corr_path = figures / f"correlation_matrix_{year}.png"
    _plot_correlation_heatmap(corr, f"Feature correlation — {year}", corr_path)
    log(f"Correlation heatmap saved: {corr_path}")

    threshold = cfg.analysis.correlation_threshold
    log(f"\nCorrelated pairs (|r| > {threshold}):")
    pairs = []
    for i in range(len(feature_cols)):
        for j in range(i + 1, len(feature_cols)):
            r = corr.iloc[i, j]
            if abs(r) > threshold:
                pairs.append((feature_cols[i], feature_cols[j], r))
                log(f"  {feature_cols[i]:24s} <-> {feature_cols[j]:24s}  r = {r:+.3f}")
    if not pairs:
        log("  none found")

    # --- VIF ---
    vif_df = compute_vif(df, feature_cols)
    log("\nVariance Inflation Factors:")
    for _, row in vif_df.iterrows():
        flag = "  <-- HIGH" if row["VIF"] > cfg.analysis.vif_threshold else ""
        log(f"  {row['Feature']:24s}  VIF = {row['VIF']:10.2f}{flag}")
    vif_path = tables / f"vif_analysis_{year}.csv"
    vif_df.to_csv(vif_path, index=False)
    log(f"VIF table saved: {vif_path}")

    # --- Preliminary RF importance ---
    X = df[feature_cols].fillna(0).values
    y = df[cfg.training.class_property].values
    rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(X, y)
    importance = pd.DataFrame(
        {"Feature": feature_cols, "Importance": rf.feature_importances_}
    ).sort_values("Importance", ascending=False)
    log("\nPreliminary RF feature importance:")
    for _, row in importance.iterrows():
        bar = "#" * int(row["Importance"] * 100)
        log(f"  {row['Feature']:24s}  {row['Importance']:.4f}  {bar}")
    imp_path = tables / f"feature_importance_{year}.csv"
    importance.to_csv(imp_path, index=False)
    log(f"Feature importance saved: {imp_path}")

    # --- Guidance (analysis never prunes automatically) ---
    sel_path = cfg.resolve_path(cfg.classifier.feature_selection, year)
    log("\n" + "=" * 60)
    log("PRUNING RECOMMENDATIONS")
    log("=" * 60)
    log(f"For each correlated pair (|r| > {threshold}), keep the feature with the")
    log("higher RF importance. When you have decided, write your selection to:")
    log(f"  {sel_path}")
    log('  format: {"features": ["SAVI", "NDMI", ...]}')
    log("Then run `lulc classify`. Without that file, ALL features are used.")

    return {
        "correlation": corr,
        "correlated_pairs": pairs,
        "vif": vif_df,
        "importance": importance,
        "paths": {"correlation": corr_path, "vif": vif_path, "importance": imp_path},
    }


def load_selected_features(cfg: LulcConfig, year: int, log=print) -> list[str] | None:
    """The user's pruned feature list, or None to use all features."""
    sel_path = cfg.resolve_path(cfg.classifier.feature_selection, year)
    if sel_path.exists():
        with open(sel_path, encoding="utf-8") as f:
            data = json.load(f)
        features = data["features"]
        log(f"Using {len(features)} selected features from {sel_path}")
        return features
    log(f"No feature selection file at {sel_path}; using ALL features.")
    return None
