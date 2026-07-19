# Contributing to geeflow

Thanks for your interest! Contributions of all kinds are welcome — bug reports, docs
fixes, new index definitions, sensor support, MCP tools, and the bigger roadmap items
(see the README's Roadmap section).

This is a monorepo with two packages: `packages/geeflow` (core GEE workflows + MCP
server) and `packages/lulc-engine` (the LULC classification toolkit built on it).

## Getting started

```bash
git clone https://github.com/prahaladuk2208-arch/geeflow
cd geeflow
python -m venv .venv
.venv/Scripts/activate        # Windows; use .venv/bin/activate on macOS/Linux
pip install -e packages/geeflow[dev] -e packages/lulc-engine[dev]
```

## Running checks

```bash
ruff check packages                    # lint (config in ruff.toml)
pytest packages/geeflow/tests -q       # geeflow unit tests
pytest packages/lulc-engine/tests -q   # lulc-engine unit tests
```

Unit tests must pass without any Earth Engine credentials — a mock stands in for the
`ee` module. If your change touches real GEE behavior, add an opt-in integration test
in `tests/integration/` (marked `@pytest.mark.gee`) and run it with:

```bash
LULC_GEE_TESTS=1 LULC_GEE_PROJECT=<your-gee-project> pytest -m gee
```

## Guidelines

- **No secrets or personal data** in code, configs, examples or tests — no project IDs
  from real research projects, no service-account files, no coordinates of unpublished
  study sites. Example AOIs must be generic/public.
- **Config over hardcoding**: new behavior should be driven by `lulc.yaml` (see
  `packages/lulc-engine/src/lulc_engine/config/schema.py`) or geeflow specs
  (`packages/geeflow/src/geeflow/specs.py`) with sensible defaults.
- **Never auto-prune features**: analysis reports evidence; the user decides what to
  drop. Don't add code that silently removes features.
- **Server-side first** for the GEE backend: keep operations in `ee.*` and minimize
  `.getInfo()` round-trips.
- Match the existing style (ruff-formatted, type hints, docstrings explaining the
  *why*).

## Proposing larger features

Open an issue first describing the use case — especially for new backends, data
sources, or dependencies. It saves everyone time if we agree on the shape before code
is written.
