# Contributing to lulc-engine

Thanks for your interest! Contributions of all kinds are welcome — bug reports, docs
fixes, new index definitions, sensor support, and the bigger roadmap items (see the
README's Roadmap section).

## Getting started

```bash
git clone https://github.com/prahaladuk2208-arch/lulc-engine
cd lulc-engine
python -m venv .venv
.venv/Scripts/activate        # Windows; use .venv/bin/activate on macOS/Linux
pip install -e .[dev]
```

## Running checks

```bash
ruff check src tests    # lint
pytest -q               # unit tests (no Earth Engine account needed)
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
  `src/lulc_engine/config/schema.py`) with sensible defaults.
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
