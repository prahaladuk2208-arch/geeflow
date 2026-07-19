"""Per-sensor cloud masking and radiometric scaling."""

from __future__ import annotations

import ee


def mask_landsat_c2_sr(image):
    """Cloud mask for Landsat Collection 2 Level 2 (L5/7/8/9).

    QA_PIXEL bit 3 = cloud, bit 4 = cloud shadow. Applies the Collection 2 L2
    surface-reflectance scaling (x 0.0000275 - 0.2).
    """
    qa = image.select("QA_PIXEL")
    cloud_bit = 1 << 3
    shadow_bit = 1 << 4
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(shadow_bit).eq(0))
    optical = image.select("SR_B.").multiply(0.0000275).add(-0.2)
    return image.addBands(optical, overwrite=True).updateMask(mask)


def mask_sentinel2_sr(image):
    """Cloud mask for Sentinel-2 SR Harmonized via the Scene Classification Layer.

    Masks SCL classes 3 (cloud shadow), 7 (unclassified), 8/9 (cloud medium/high
    probability) and 10 (thin cirrus); scales reflectance to 0-1.
    """
    scl = image.select("SCL")
    mask = (
        scl.neq(3)
        .And(scl.neq(7))
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
    )
    core_bands = ["B2", "B3", "B4", "B8", "B11", "B12"]
    extra_bands = ["B5", "B6", "B7", "B8A"]
    optical = image.select(core_bands + extra_bands).divide(10000)
    return image.addBands(optical, overwrite=True).updateMask(mask)


def mask_mss_c2(image):
    """Cloud mask for Landsat MSS Collection 2 (raw DN); QA_PIXEL bits 3 and 4."""
    qa = image.select("QA_PIXEL")
    mask = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
    return image.updateMask(mask)


def convert_mss_toa(image):
    """Convert MSS raw DN to top-of-atmosphere reflectance using image metadata."""
    return ee.Algorithms.Landsat.TOA(image)
