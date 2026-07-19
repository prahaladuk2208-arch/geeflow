"""Earth Engine session setup (interactive user auth or service account)."""

from __future__ import annotations

import json
from pathlib import Path

import ee


def init_ee(project_id: str | None = None, service_account_key: str | Path | None = None) -> None:
    """Initialize Earth Engine.

    With a service-account key file, credentials come from the key (the client email is
    read out of the JSON). Otherwise the cached user credentials from `lulc auth` are used.
    """
    if service_account_key is not None:
        key_path = Path(service_account_key)
        with open(key_path, encoding="utf-8") as f:
            client_email = json.load(f)["client_email"]
        credentials = ee.ServiceAccountCredentials(client_email, str(key_path))
        ee.Initialize(credentials, project=project_id)
    else:
        ee.Initialize(project=project_id)


def authenticate() -> None:
    """Run the interactive Earth Engine authentication flow."""
    ee.Authenticate()
