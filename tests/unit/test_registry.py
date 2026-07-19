from lulc_engine.features.indices import computable_indices
from lulc_engine.sensors.harmonize import harmonized_bands_for
from lulc_engine.sensors.registry import COLLECTIONS, get_sensors_for_year


def test_sensor_priority_by_year():
    assert get_sensors_for_year(1975)[0].startswith("landsat_mss_")
    assert get_sensors_for_year(1995) == ["landsat5_t1_sr"]
    assert get_sensors_for_year(2010) == ["landsat5_t1_sr", "landsat7_t1_sr"]
    assert get_sensors_for_year(2013) == ["landsat8_sr"]
    assert get_sensors_for_year(2020) == ["sentinel2_sr", "landsat8_sr"]
    assert get_sensors_for_year(2025) == ["sentinel2_sr", "landsat9_sr"]


def test_all_sensor_keys_have_collections():
    for year in (1975, 1980, 1990, 2000, 2013, 2018, 2024):
        for key in get_sensors_for_year(year):
            assert key in COLLECTIONS


def test_harmonized_bands():
    assert harmonized_bands_for("landsat5_t1_sr") == ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"]
    s2 = harmonized_bands_for("sentinel2_sr")
    assert "RedEdge1" in s2 and "SWIR2" in s2
    mss = harmonized_bands_for("landsat_mss_l1")
    assert "NIR" in mss and "Blue" not in mss


def test_mss_era_gets_reduced_index_set():
    mss_bands = harmonized_bands_for("landsat_mss_l1")
    wanted = ["NDVI", "SAVI", "EVI", "NDMI", "NBR", "GreenRed"]
    computable = computable_indices(wanted, mss_bands)
    # EVI needs Blue, NDMI/NBR need SWIR -> automatically dropped for MSS
    assert computable == ["NDVI", "SAVI", "GreenRed"]


def test_full_index_set_for_tm():
    tm_bands = harmonized_bands_for("landsat5_t1_sr")
    wanted = ["NDVI", "SAVI", "EVI", "NDMI", "NBR", "BlueGreenNIR", "GreenRed"]
    assert computable_indices(wanted, tm_bands) == wanted
