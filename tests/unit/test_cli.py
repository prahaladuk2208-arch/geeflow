from typer.testing import CliRunner

from lulc_engine import __version__
from lulc_engine.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_and_validate(tmp_path):
    result = runner.invoke(
        app, ["init", "--name", "demo", "--template", "forest", "--dir", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "lulc.yaml").exists()
    assert (tmp_path / "training").is_dir()

    result = runner.invoke(app, ["validate", "-c", str(tmp_path / "lulc.yaml")])
    assert result.exit_code == 0, result.output
    assert "Config OK" in result.output
    assert "2022" in result.output  # run plan lists template years


def test_init_refuses_overwrite(tmp_path):
    (tmp_path / "lulc.yaml").write_text("x", encoding="utf-8")
    result = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "not overwriting" in result.output


def test_init_unknown_template(tmp_path):
    result = runner.invoke(app, ["init", "--template", "nope", "--dir", str(tmp_path)])
    assert result.exit_code == 1


def test_validate_reports_config_errors(tmp_path):
    bad = tmp_path / "lulc.yaml"
    bad.write_text("aoi: {}\nclasses: {0: A, 1: B}\n", encoding="utf-8")
    result = runner.invoke(app, ["validate", "-c", str(bad)])
    assert result.exit_code == 1
    assert "exactly one" in result.output


def test_validate_example_configs():
    from pathlib import Path

    EXAMPLES = Path(__file__).parent.parent.parent / "examples"
    for example in ("forest_monitoring", "historical_landsat"):
        result = runner.invoke(app, ["validate", "-c", str(EXAMPLES / example / "lulc.yaml")])
        assert result.exit_code == 0, result.output
