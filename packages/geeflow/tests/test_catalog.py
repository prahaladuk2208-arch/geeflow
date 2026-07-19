import pytest

from geeflow import catalog

FAKE_CATALOG = [
    {
        "id": "COPERNICUS/S2_SR_HARMONIZED",
        "title": "Harmonized Sentinel-2 MSI: MultiSpectral Instrument, Level-2A (SR)",
        "type": "image_collection",
        "tags": "copernicus, esa, msi, sentinel",
        "provider": "European Union/ESA/Copernicus",
    },
    {
        "id": "LANDSAT/LT05/C02/T1_L2",
        "title": "USGS Landsat 5 Level 2, Collection 2, Tier 1",
        "type": "image_collection",
        "tags": "landsat, usgs",
        "provider": "USGS",
    },
]


@pytest.fixture(autouse=True)
def fake_catalog(monkeypatch):
    monkeypatch.setattr(catalog, "load_catalog", lambda refresh=False: FAKE_CATALOG)


def test_partial_terms_still_match():
    # "surface reflectance" is not in the title verbatim; partial match must still hit
    hits = catalog.search("sentinel-2 surface reflectance harmonized", limit=3)
    assert hits and hits[0]["id"] == "COPERNICUS/S2_SR_HARMONIZED"


def test_ranking_prefers_more_matched_terms():
    hits = catalog.search("landsat collection tier", limit=2)
    assert hits[0]["id"] == "LANDSAT/LT05/C02/T1_L2"


def test_no_match_returns_empty():
    assert catalog.search("modis ocean chlorophyll") == []


def test_empty_query_returns_empty():
    assert catalog.search("   ") == []


def test_dataset_entry_exact():
    assert catalog.dataset_entry("LANDSAT/LT05/C02/T1_L2")["provider"] == "USGS"
    assert catalog.dataset_entry("NOPE/NOPE") is None
