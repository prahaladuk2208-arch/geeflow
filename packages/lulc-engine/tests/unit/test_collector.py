from lulc_engine.collector import render_collector


def test_s2_collector_renders(forest_example_config):
    js = render_collector(forest_example_config, 2022)
    assert "COPERNICUS/S2_SR_HARMONIZED" in js
    assert "ee.Geometry.Point(37.31, -0.15).buffer(15000" in js
    # both seasons with correct windows
    assert "'2022-01-01', '2022-03-31'" in js
    assert "'2022-10-01', '2022-12-31'" in js
    # class variables sanitized from names
    for var in ("Forest", "Agriculture", "Water", "Builtup"):
        assert var in js
    assert "training_2022.geojson" in js
    # SCL masking for S2
    assert "SCL" in js


def test_tm_collector_renders(historical_example_config):
    js = render_collector(historical_example_config, 1995)
    assert "LANDSAT/LT05/C02/T1_L2" in js
    assert "QA_PIXEL" in js
    assert "0.0000275" in js  # C2 L2 scaling
    assert "Vegetated" in js and "NonVegetated" in js


def test_mss_collector_uses_toa(historical_example_config):
    js = render_collector(historical_example_config, 1978)
    assert "LANDSAT/LM" in js
    assert "ee.Algorithms.Landsat.TOA" in js
    # single season -> no delta layer
    assert "delta_NDVI" not in js
    # MSS has no SWIR -> no NDMI panel entry
    assert "NDMI" not in js
