"""Band renaming to the standard harmonized namespace, plus per-sensor collection prep."""

from __future__ import annotations

import ee

from geeflow.sensors import masking
from geeflow.sensors.registry import (
    COLLECTIONS,
    LANDSAT57_BAND_MAP,
    LANDSAT89_BAND_MAP,
    MSS_BAND_MAP,
    SENTINEL2_BAND_MAP,
    SENTINEL2_EXTRA_BANDS,
)


def harmonize_landsat57(image):
    return image.select(list(LANDSAT57_BAND_MAP.keys()), list(LANDSAT57_BAND_MAP.values()))


def harmonize_landsat89(image):
    return image.select(list(LANDSAT89_BAND_MAP.keys()), list(LANDSAT89_BAND_MAP.values()))


def harmonize_sentinel2(image):
    all_bands = {**SENTINEL2_BAND_MAP, **SENTINEL2_EXTRA_BANDS}
    return image.select(list(all_bands.keys()), list(all_bands.values()))


def harmonize_mss(image):
    return image.select(list(MSS_BAND_MAP.keys()), list(MSS_BAND_MAP.values()))


def get_collection(sensor_key: str, aoi, start_date: str, end_date: str):
    """A filtered, cloud-masked, harmonized ee.ImageCollection for one sensor."""
    collection_id = COLLECTIONS[sensor_key]
    col = ee.ImageCollection(collection_id).filterBounds(aoi).filterDate(start_date, end_date)

    if sensor_key in ("landsat5_t1_sr", "landsat7_t1_sr"):
        col = col.map(masking.mask_landsat_c2_sr).map(harmonize_landsat57)
    elif sensor_key in ("landsat8_sr", "landsat9_sr"):
        col = col.map(masking.mask_landsat_c2_sr).map(harmonize_landsat89)
    elif sensor_key == "sentinel2_sr":
        col = col.map(masking.mask_sentinel2_sr).map(harmonize_sentinel2)
    elif sensor_key.startswith("landsat_mss_"):
        col = col.map(masking.mask_mss_c2).map(masking.convert_mss_toa).map(harmonize_mss)
    else:
        raise ValueError(f"Unknown sensor key: {sensor_key}")

    return col


def harmonized_bands_for(sensor_key: str) -> list[str]:
    """Band names a harmonized image from this sensor will carry."""
    if sensor_key in ("landsat5_t1_sr", "landsat7_t1_sr"):
        return list(LANDSAT57_BAND_MAP.values())
    if sensor_key in ("landsat8_sr", "landsat9_sr"):
        return list(LANDSAT89_BAND_MAP.values())
    if sensor_key == "sentinel2_sr":
        return list(SENTINEL2_BAND_MAP.values()) + list(SENTINEL2_EXTRA_BANDS.values())
    if sensor_key.startswith("landsat_mss_"):
        return list(MSS_BAND_MAP.values())
    raise ValueError(f"Unknown sensor key: {sensor_key}")
