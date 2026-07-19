"""Built-in defaults: sensor eras and the canonical index/texture registries.

These encode widely applicable conventions for multi-decade Landsat/Sentinel-2 work:
MSS era through 1983 at 60 m (sparse archive, so sensors are merged and the search
window is always widened), TM/ETM+/OLI era through 2013 at 30 m, Sentinel-2 era
afterwards at 10 m. Everything here can be overridden in lulc.yaml.
"""

from __future__ import annotations

# Raw era definitions; materialized into SensorEra models by the schema's default_factory.
DEFAULT_SENSOR_ERAS: list[dict] = [
    {
        "name": "mss",
        "max_year": 1983,
        "scale_m": 60,
        "search_window_yr": 2,
        "merge_sensors": True,
        "always_expand": True,
    },
    {"name": "tm", "max_year": 2013, "scale_m": 30, "search_window_yr": 1},
    {"name": "s2", "max_year": 9999, "scale_m": 10, "search_window_yr": 1},
]

# Canonical spectral index registry: name -> required standard bands.
# The actual ee.Image builders live in lulc_engine.features.indices; an index is only
# computed for a composite when all its required bands are present, which is how
# band-poor eras (e.g. MSS without Blue/SWIR) automatically get a reduced set.
KNOWN_INDICES: dict[str, list[str]] = {
    "NDVI": ["NIR", "Red"],
    "SAVI": ["NIR", "Red"],
    "EVI": ["NIR", "Red", "Blue"],
    "NDMI": ["NIR", "SWIR1"],
    "NBR": ["NIR", "SWIR2"],
    "BlueGreenNIR": ["Blue", "Green", "NIR"],
    "GreenRed": ["Green", "Red"],
    "NDRE": ["NIR", "RedEdge1"],
    "CIre": ["NIR", "RedEdge1"],
    "NDWI": ["Green", "NIR"],
    "NDBI": ["SWIR1", "NIR"],
}

KNOWN_TEXTURE_METRICS = {"entropy", "contrast", "variance", "correlation"}
