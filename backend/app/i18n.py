"""All user-facing text, in the language set by APP_LANGUAGE.

Texts live in app/locales/<language>.json. The frontend gets the same texts
from /api/meta, so changing APP_LANGUAGE switches the whole app.
"""

import json
from functools import cache
from pathlib import Path

from app.config import settings

LOCALES = Path(__file__).resolve().parent / "locales"
FALLBACK = "en"

FIELDS = (
    "successful_tenderer",
    "contracting_authority",
    "location",
    "amount_awarded",
    "downside_amount",
    "publication_date",
    "award_date",
    "cpv",
)

# Filter parameter -> (field, suffix key) for labelling active filters in exports.
_FILTER_PARTS = {
    "cpv": ("cpv", "filters.starts_with"),
    "amount_awarded_min": ("amount_awarded", "filters.min"),
    "amount_awarded_max": ("amount_awarded", "filters.max"),
    "downside_min": ("downside_amount", "filters.min"),
    "downside_max": ("downside_amount", "filters.max"),
    "publication_date_from": ("publication_date", "filters.from"),
    "publication_date_to": ("publication_date", "filters.to"),
    "award_date_from": ("award_date", "filters.from"),
    "award_date_to": ("award_date", "filters.to"),
}


def _load(language: str) -> dict[str, str]:
    path = LOCALES / f"{language}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@cache
def messages() -> dict[str, str]:
    """Texts for the configured language; missing keys fall back to English."""
    return {**_load(FALLBACK), **_load(settings.app_language)}


def t(key: str, **values) -> str:
    text = messages().get(key, key)
    return text.format(**values) if values else text


def field_labels() -> dict[str, str]:
    return {f: t(f"fields.{f}") for f in FIELDS}


def dimension_label(key: str) -> str:
    return t(f"fields.{key}") if key in FIELDS else t(f"dimensions.{key}")


def filter_label(key: str) -> str:
    if key in _FILTER_PARTS:
        field, suffix = _FILTER_PARTS[key]
        return f"{t(f'fields.{field}')} ({t(suffix)})"
    return t(f"fields.{key}")
