"""Shared fixtures.

Unit tests never touch the real Earth Engine API. Unless LULC_GEE_TESTS=1 is set, a
MagicMock stands in for the `ee` module so importing pipeline code needs no credentials
and constructing ee objects performs no network calls.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

if not os.environ.get("LULC_GEE_TESTS"):
    sys.modules.setdefault("ee", mock.MagicMock(name="ee"))

import pytest  # noqa: E402

from lulc_engine.config import load_config  # noqa: E402

EXAMPLES = Path(__file__).parent.parent / "examples"
DATA = Path(__file__).parent / "data"


MINIMAL_YAML = """
project:
  name: test-project
aoi:
  center_buffer: { lat: 10.0, lon: 20.0, radius_m: 5000 }
time_points: [2020, 1980, 2005]
classes:
  0: Forest
  1: Other
"""


@pytest.fixture
def minimal_config(tmp_path):
    cfg_path = tmp_path / "lulc.yaml"
    cfg_path.write_text(MINIMAL_YAML, encoding="utf-8")
    return load_config(cfg_path)


@pytest.fixture
def forest_example_config():
    return load_config(EXAMPLES / "forest_monitoring" / "lulc.yaml")


@pytest.fixture
def historical_example_config():
    return load_config(EXAMPLES / "historical_landsat" / "lulc.yaml")
