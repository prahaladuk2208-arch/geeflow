"""Earth Engine data catalog search.

Uses the community-maintained flat catalog JSON (a mirror of the official GEE STAC
catalog) so search works with a single cached download instead of crawling STAC.
"""

from __future__ import annotations

import json
import tempfile
import time
import urllib.request
from pathlib import Path

CATALOG_URL = (
    "https://raw.githubusercontent.com/samapriya/Earth-Engine-Datasets-List/"
    "master/gee_catalog.json"
)
_CACHE_TTL_S = 7 * 24 * 3600  # the catalog changes slowly; refresh weekly


def _cache_path() -> Path:
    return Path(tempfile.gettempdir()) / "geeflow_gee_catalog.json"


def load_catalog(refresh: bool = False) -> list[dict]:
    """The full dataset catalog, cached locally. Raises RuntimeError when offline."""
    cache = _cache_path()
    if not refresh and cache.exists() and (time.time() - cache.stat().st_mtime) < _CACHE_TTL_S:
        with open(cache, encoding="utf-8") as f:
            return json.load(f)
    try:
        with urllib.request.urlopen(CATALOG_URL, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except OSError as e:
        if cache.exists():  # stale cache beats no data
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
        raise RuntimeError(
            f"could not download the GEE catalog index ({e}); check your connection"
        ) from e
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def search(query: str, limit: int = 10) -> list[dict]:
    """Search dataset ids/titles/tags/providers. Returns compact result dicts.

    Case-insensitive ranked match: entries matching more of the space-separated terms
    rank higher; at least one term must match. (Strict all-terms matching is too
    brittle — e.g. "surface reflectance" appears as "(SR)" in many titles.)
    """
    terms = [t.lower() for t in query.split() if t]
    if not terms:
        return []
    scored = []
    for entry in load_catalog():
        haystack = " ".join(
            str(entry.get(k, ""))
            for k in ("id", "title", "tags", "provider", "type")
        ).lower()
        score = sum(1 for t in terms if t in haystack)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda se: -se[0])
    return [
        {
            "id": e.get("id"),
            "title": e.get("title"),
            "type": e.get("type"),
            "start_date": e.get("start_date"),
            "end_date": e.get("end_date"),
            "provider": e.get("provider"),
            "matched_terms": s,
        }
        for s, e in scored[:limit]
    ]


def dataset_entry(dataset_id: str) -> dict | None:
    """The catalog entry for an exact dataset id, or None."""
    for entry in load_catalog():
        if entry.get("id") == dataset_id:
            return entry
    return None
