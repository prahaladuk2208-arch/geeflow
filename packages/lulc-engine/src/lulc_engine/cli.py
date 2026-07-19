"""The `lulc` command-line interface. Every command wraps a Python API function."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(
    name="lulc",
    help="Config-driven LULC classification workflows on Google Earth Engine.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
labels_app = typer.Typer(help="Training-data commands.", no_args_is_help=True)
app.add_typer(labels_app, name="labels")

ConfigOpt = typer.Option("lulc.yaml", "--config", "-c", help="Path to the project lulc.yaml")
YearOpt = typer.Option(..., "--year", "-y", help="Target year")


def _load(config: str):
    from lulc_engine.config import ConfigError, load_config

    try:
        return load_config(config)
    except ConfigError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from e


def _pipeline(config: str):
    from lulc_engine.pipeline import Pipeline

    return Pipeline(_load(config))


@app.command()
def init(
    name: str = typer.Option("my-lulc-project", "--name", help="Project name"),
    template: str = typer.Option("forest", "--template", help="Config template: forest | basic"),
    directory: Path = typer.Option(Path("."), "--dir", help="Directory to scaffold into"),
):
    """Scaffold a new project: lulc.yaml + training/ + outputs/ folders."""
    from jinja2 import Environment, PackageLoader

    class_schemes = {
        "forest": [(0, "Forest"), (1, "Agriculture"), (2, "Water"), (3, "Built-up")],
        "basic": [(0, "Vegetated"), (1, "Non-Vegetated")],
    }
    if template not in class_schemes:
        typer.secho(f"unknown template {template!r}; choose from {list(class_schemes)}", fg=typer.colors.RED)
        raise typer.Exit(1)

    directory.mkdir(parents=True, exist_ok=True)
    config_path = directory / "lulc.yaml"
    if config_path.exists():
        typer.secho(f"{config_path} already exists; not overwriting.", fg=typer.colors.RED)
        raise typer.Exit(1)

    env = Environment(loader=PackageLoader("lulc_engine", "templates"), keep_trailing_newline=True)
    rendered = env.get_template("project_lulc.yaml.j2").render(
        name=name, gee_project_id="my-gee-project", classes=class_schemes[template]
    )
    config_path.write_text(rendered, encoding="utf-8")
    (directory / "training").mkdir(exist_ok=True)
    (directory / "outputs").mkdir(exist_ok=True)

    typer.secho(f"Created {config_path}", fg=typer.colors.GREEN)
    typer.echo("Next steps:")
    typer.echo("  1. Edit lulc.yaml (AOI, gee_project_id, classes, seasons, years)")
    typer.echo("  2. lulc auth")
    typer.echo("  3. lulc validate -c lulc.yaml")


@app.command()
def auth(
    service_account: Path | None = typer.Option(
        None, "--service-account", help="Service-account key JSON (skips interactive auth)"
    ),
):
    """Authenticate with Google Earth Engine."""
    from geeflow import session as ee_session

    if service_account:
        ee_session.init_ee(service_account_key=service_account)
        typer.secho("Service-account credentials OK.", fg=typer.colors.GREEN)
    else:
        ee_session.authenticate()
        typer.secho("Authentication complete. Run `lulc validate` next.", fg=typer.colors.GREEN)


@app.command()
def validate(config: str = ConfigOpt):
    """Validate the config and print the resolved run plan."""
    from geeflow.composite.builder import sensors_for

    cfg = _load(config)
    typer.secho(f"Config OK: {config}", fg=typer.colors.GREEN)
    typer.echo(f"\nProject: {cfg.project.name} (backend={cfg.project.backend})")
    typer.echo(f"GEE project: {cfg.project.gee_project_id or '(default credentials)'}")

    if cfg.aoi.center_buffer:
        cb = cfg.aoi.center_buffer
        typer.echo(f"AOI: {cb.radius_m / 1000:.1f} km buffer around ({cb.lat}, {cb.lon})")
    elif cfg.aoi.geojson:
        typer.echo(f"AOI: {cfg.aoi.geojson}")
    else:
        typer.echo(f"AOI: {cfg.aoi.ee_asset}")

    typer.echo("Classes: " + ", ".join(f"{k}={v}" for k, v in cfg.sorted_class_items()))
    typer.echo("Seasons: " + ", ".join(f"{s.name}({s.months[0]}-{s.months[1]})" for s in cfg.seasons)
               + f"  [reference: {cfg.reference_season.name}]")
    typer.echo(f"Indices: {', '.join(cfg.features.indices)}")
    typer.echo("\nRun plan:")
    for year in cfg.time_points:
        era = cfg.era_for_year(year)
        typer.echo(f"  {year}: era={era.name:6s} scale={era.scale_m:3d}m "
                   f"sensors={sensors_for(year, era)}")
    if not cfg.time_points:
        typer.secho("  (no time_points configured)", fg=typer.colors.YELLOW)


@app.command()
def check(
    config: str = ConfigOpt,
    years: str = typer.Option(None, "--years", help="Comma-separated years (default: all)"),
):
    """Report scene availability per year/season/sensor."""
    pipe = _pipeline(config)
    year_list = [int(y) for y in years.split(",")] if years else None
    pipe.check(year_list)


@app.command()
def composite(config: str = ConfigOpt, year: int = YearOpt):
    """Build the seasonal composites for a year (prints scene counts)."""
    pipe = _pipeline(config)
    composites, sensor, bands = pipe.build_composites(year)
    typer.secho(
        f"\nBuilt {len(composites)} composites ({', '.join(composites)}) "
        f"from {sensor}; bands: {bands}",
        fg=typer.colors.GREEN,
    )


@app.command()
def features(config: str = ConfigOpt, year: int = YearOpt):
    """Build the full candidate feature stack for a year and list its bands."""
    pipe = _pipeline(config)
    stack = pipe.build_features(year)
    band_names = stack.bandNames().getInfo()
    scale = pipe.cfg.scale_for_year(year)
    typer.secho(f"\nFeature stack {year}: {len(band_names)} bands at {scale} m", fg=typer.colors.GREEN)
    for b in band_names:
        typer.echo(f"  {b}")


@app.command()
def analyze(config: str = ConfigOpt, year: int = YearOpt):
    """Correlation + VIF + preliminary importance reports (never auto-prunes)."""
    pipe = _pipeline(config)
    pipe.analyze(year)


@app.command()
def classify(
    config: str = ConfigOpt,
    year: int = YearOpt,
    no_export: bool = typer.Option(False, "--no-export", help="Skip starting the export task"),
):
    """Cross-validate RF/GBT/SVM, train the best in GEE, classify and export."""
    pipe = _pipeline(config)
    result = pipe.classify(year, export=not no_export)
    typer.secho(f"\nDone. Best classifier: {result['best_classifier']}", fg=typer.colors.GREEN)


@app.command()
def run(
    config: str = ConfigOpt,
    years: str = typer.Option(None, "--years", help="Comma-separated years (default: all)"),
    no_export: bool = typer.Option(False, "--no-export", help="Skip export tasks"),
):
    """Classify every configured time point (or a subset)."""
    pipe = _pipeline(config)
    year_list = [int(y) for y in years.split(",")] if years else None
    pipe.run(year_list, export=not no_export)


@labels_app.command("template")
def labels_template(
    config: str = ConfigOpt,
    year: int = YearOpt,
    out: Path | None = typer.Option(None, "--out", help="Output path (default: collector_<year>.js)"),
):
    """Generate the GEE Code Editor collector script for drawing training polygons."""
    from lulc_engine.collector import render_collector

    cfg = _load(config)
    script = render_collector(cfg, year)
    out = out or Path(f"collector_{year}.js")
    out.write_text(script, encoding="utf-8")
    typer.secho(f"Collector script written: {out}", fg=typer.colors.GREEN)
    typer.echo("Paste it into https://code.earthengine.google.com/ and follow the header comments.")


@labels_app.command("import")
def labels_import(
    config: str = ConfigOpt,
    year: int = YearOpt,
    file: Path = typer.Option(..., "--file", "-f", help="Training vector file (GeoJSON)"),
):
    """Validate a training file and copy it into the project's training path."""
    import shutil

    from lulc_engine.labels.loaders import parse_training_file, summarize

    cfg = _load(config)
    parsed, warnings = parse_training_file(file, cfg.training.class_property)
    summary = summarize(parsed, cfg, str(file))
    typer.echo(f"{summary.n_features} features in {file}")
    for code, name in cfg.sorted_class_items():
        typer.echo(f"  class {code} ({name}): {summary.class_counts.get(code, 0)}")
    for w in warnings + summary.warnings:
        typer.secho(f"  WARNING: {w}", fg=typer.colors.YELLOW)

    dest = cfg.resolve_path(cfg.training.path, year)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if file.resolve() != dest.resolve():
        shutil.copyfile(file, dest)
        typer.secho(f"Copied to {dest}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"File already at {dest}", fg=typer.colors.GREEN)


@app.command()
def version():
    """Print the lulc-engine version."""
    from lulc_engine import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
