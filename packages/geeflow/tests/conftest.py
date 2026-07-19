"""geeflow test fixtures.

Unless LULC_GEE_TESTS=1 is set, a MagicMock stands in for the `ee` module so importing
geeflow needs no credentials and constructing ee objects performs no network calls.
"""

from __future__ import annotations

import os
import sys
from unittest import mock

if not os.environ.get("LULC_GEE_TESTS"):
    sys.modules.setdefault("ee", mock.MagicMock(name="ee"))
