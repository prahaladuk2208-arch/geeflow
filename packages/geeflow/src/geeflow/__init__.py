"""geeflow: Google Earth Engine workflows made easy.

Harmonized multi-sensor composites (Landsat MSS through Sentinel-2), spectral index
registry, seasonal phenology features, exports and visualization — as a Python library
and as an MCP server (`geeflow-mcp`) for AI-assisted analysis.
"""

__version__ = "0.1.0"

from geeflow.specs import (
    KNOWN_INDICES,
    CompositeSpec,
    Season,
    SeasonalSpec,
    SensorEra,
    TextureSpec,
    default_sensor_eras,
    era_for_year,
)

__all__ = [
    "KNOWN_INDICES",
    "CompositeSpec",
    "Season",
    "SeasonalSpec",
    "SensorEra",
    "TextureSpec",
    "__version__",
    "default_sensor_eras",
    "era_for_year",
]
