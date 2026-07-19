"""Sensor registry: GEE collection ids, band harmonization maps, year -> sensor priority."""

from __future__ import annotations

# Earth Engine collection ids, keyed by sensor key used throughout the package.
COLLECTIONS: dict[str, str] = {
    "landsat_mss_l1": "LANDSAT/LM01/C02/T1",
    "landsat_mss_l2": "LANDSAT/LM02/C02/T1",
    "landsat_mss_l3": "LANDSAT/LM03/C02/T1",
    "landsat_mss_l4": "LANDSAT/LM04/C02/T1",
    "landsat_mss_l5": "LANDSAT/LM05/C02/T1",
    "landsat5_t1_sr": "LANDSAT/LT05/C02/T1_L2",
    "landsat7_t1_sr": "LANDSAT/LE07/C02/T1_L2",
    "landsat8_sr": "LANDSAT/LC08/C02/T1_L2",
    "landsat9_sr": "LANDSAT/LC09/C02/T1_L2",
    "sentinel2_sr": "COPERNICUS/S2_SR_HARMONIZED",
    "alphaearth": "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
}

# Standardized band names used for all harmonized composites.
STANDARD_BANDS = ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"]

# Landsat 5/7 TM/ETM+ (Collection 2 Level 2)
LANDSAT57_BAND_MAP = {
    "SR_B1": "Blue",
    "SR_B2": "Green",
    "SR_B3": "Red",
    "SR_B4": "NIR",
    "SR_B5": "SWIR1",
    "SR_B7": "SWIR2",
}

# Landsat 8/9 OLI (Collection 2 Level 2)
LANDSAT89_BAND_MAP = {
    "SR_B2": "Blue",
    "SR_B3": "Green",
    "SR_B4": "Red",
    "SR_B5": "NIR",
    "SR_B6": "SWIR1",
    "SR_B7": "SWIR2",
}

# Sentinel-2 SR Harmonized core bands
SENTINEL2_BAND_MAP = {
    "B2": "Blue",
    "B3": "Green",
    "B4": "Red",
    "B8": "NIR",
    "B11": "SWIR1",
    "B12": "SWIR2",
}

# Sentinel-2 red-edge + narrow NIR (20 m native, resampled to 10 m by GEE)
SENTINEL2_EXTRA_BANDS = {
    "B5": "RedEdge1",
    "B6": "RedEdge2",
    "B7": "RedEdge3",
    "B8A": "NIR_narrow",
}

# Landsat MSS. B6 is the primary near-infrared channel and maps to the standard "NIR"
# name so the generic index registry (NDVI etc.) works unchanged in the MSS era.
MSS_BAND_MAP = {
    "B4": "Green",
    "B5": "Red",
    "B6": "NIR",
    "B7": "NIR2",
}


def get_sensors_for_year(year: int) -> list[str]:
    """Default sensor keys for a year, ordered by priority (primary first)."""
    if year <= 1978:
        return ["landsat_mss_l1", "landsat_mss_l2", "landsat_mss_l3"]
    elif year <= 1982:
        return ["landsat_mss_l2", "landsat_mss_l3", "landsat_mss_l4"]
    elif year <= 1984:
        return ["landsat_mss_l4", "landsat_mss_l5"]
    elif year <= 1998:
        return ["landsat5_t1_sr"]
    elif year <= 2012:
        return ["landsat5_t1_sr", "landsat7_t1_sr"]
    elif year <= 2013:
        return ["landsat8_sr"]
    elif year <= 2021:
        return ["sentinel2_sr", "landsat8_sr"]
    else:
        return ["sentinel2_sr", "landsat9_sr"]
