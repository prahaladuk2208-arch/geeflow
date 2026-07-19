"""lulc-engine: config-driven LULC classification workflows on Google Earth Engine."""

__version__ = "0.1.0"

from lulc_engine.config import LulcConfig, load_config

__all__ = ["LulcConfig", "Pipeline", "__version__", "load_config"]


def __getattr__(name):
    # Pipeline pulls in the `ee` stack; import it lazily so config-only use stays light.
    if name == "Pipeline":
        from lulc_engine.pipeline import Pipeline

        return Pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
