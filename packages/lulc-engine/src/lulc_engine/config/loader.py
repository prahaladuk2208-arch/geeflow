"""Load and validate lulc.yaml project configurations."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from lulc_engine.config.schema import LulcConfig

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value):
    """Recursively expand ${ENV_VAR} references in string values."""
    if isinstance(value, str):

        def repl(m):
            name = m.group(1)
            if name not in os.environ:
                raise KeyError(f"config references undefined environment variable ${{{name}}}")
            return os.environ[name]

        return _ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


class ConfigError(Exception):
    """Raised when a project config cannot be loaded or validated."""


def load_config(path: str | Path) -> LulcConfig:
    """Load a lulc.yaml file into a validated LulcConfig.

    Relative paths inside the config resolve against the config file's directory.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} is not a YAML mapping")

    raw = _expand_env(raw)
    raw.setdefault("base_dir", str(path.resolve().parent))

    try:
        return LulcConfig(**raw)
    except ValidationError as e:
        lines = [f"invalid config {path}:"]
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            lines.append(f"  {loc}: {err['msg']}")
        raise ConfigError("\n".join(lines)) from e
