"""Post-classification cleanup: majority filter and minimum mapping unit."""

from __future__ import annotations

import math

from lulc_engine.config.schema import LulcConfig


def apply_postprocessing(classified, cfg: LulcConfig, year: int, log=print):
    pp = cfg.postprocess

    if pp.majority_filter.enabled:
        radius = (pp.majority_filter.kernel - 1) // 2
        log(f"Applying {pp.majority_filter.kernel}x{pp.majority_filter.kernel} majority filter...")
        classified = classified.focal_mode(
            radius=radius, kernelType="square", iterations=pp.majority_filter.iterations
        )

    if pp.min_mapping_unit_ha:
        scale = cfg.scale_for_year(year)
        pixel_ha = (scale * scale) / 10_000
        min_pixels = max(2, math.ceil(pp.min_mapping_unit_ha / pixel_ha))
        log(f"Applying minimum mapping unit: {pp.min_mapping_unit_ha} ha (~{min_pixels} px)")
        counts = classified.connectedPixelCount(min_pixels + 1, True)
        small = counts.lt(min_pixels)
        smoothed = classified.focal_mode(radius=2, kernelType="square")
        classified = classified.where(small, smoothed)

    return classified.rename("classification")
