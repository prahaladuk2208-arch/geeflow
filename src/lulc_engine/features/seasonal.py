"""Cross-season phenology features: deltas, ratios and season values.

For a reference season R and every other season S, per index X (band naming):
    delta_X_S = X(S) - X(R)          -- seasonal difference
    X_ratio_S = X(R) / max(X(S), eps) -- near 1.0 for evergreen, high for deciduous
    X_S       = X(S)                  -- the other season's raw index value

ALL candidate features are computed here; pruning happens later via the user's
correlation/VIF-informed feature selection.
"""

from __future__ import annotations

from lulc_engine.config.schema import LulcConfig

_RATIO_EPS = 0.001


def compute_seasonal_features(
    composites: dict,
    computed_indices: dict[str, list[str]],
    cfg: LulcConfig,
):
    """Stack seasonal features onto the reference-season composite.

    Args:
        composites: season name -> ee.Image (each already carries its index bands).
        computed_indices: season name -> index names actually computed for it.
        cfg: full project config.

    Returns:
        ee.Image: the reference composite with all cross-season bands appended.
    """
    ref_name = cfg.reference_season.name
    scfg = cfg.features.seasonal
    ref = composites[ref_name]

    extra_bands = []
    for season in cfg.seasons:
        if season.name == ref_name:
            continue
        other = composites[season.name]
        common = [
            i for i in computed_indices[ref_name] if i in computed_indices[season.name]
        ]

        if scfg.deltas:
            for idx in _restrict(common, scfg.delta_indices):
                extra_bands.append(
                    other.select(idx).subtract(ref.select(idx)).rename(f"delta_{idx}_{season.name}")
                )
        if scfg.ratios:
            for idx in _restrict(common, scfg.ratio_indices):
                extra_bands.append(
                    ref.select(idx)
                    .divide(other.select(idx).max(_RATIO_EPS))
                    .rename(f"{idx}_ratio_{season.name}")
                )
        if scfg.season_values:
            for idx in _restrict(common, scfg.value_indices):
                extra_bands.append(other.select(idx).rename(f"{idx}_{season.name}"))

    if not extra_bands:
        return ref
    return ref.addBands(extra_bands)


def _restrict(common: list[str], wanted: list[str] | None) -> list[str]:
    if wanted is None:
        return common
    return [i for i in common if i in wanted]
