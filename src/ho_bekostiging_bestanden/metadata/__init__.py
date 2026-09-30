"""Metadata: veldindelingen en codelijsten voor de HO-bekostigingsbestanden."""

import tomllib
from functools import lru_cache
from pathlib import Path

import polars as pl

SCHEMA_DIR = Path(__file__).parent


@lru_cache
def _lees_toml(name: str) -> dict:
    schema_path = SCHEMA_DIR / f"{name}_schema.toml"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema niet gevonden: {schema_path}")
    with open(schema_path, "rb") as f:
        return tomllib.load(f)


def load_schema(name: str) -> dict[str, dict]:
    """Laad een schema-TOML en geef de recordsoort-entries terug.

    Args:
        name: Naam van het schema zonder extensie (``"analyse"`` of
              ``"hisbek"``). Laadt ``{name}_schema.toml`` uit ``metadata/``.

    Returns:
        Dict van recordsoort naar schema-dict (``fields``, ``date_fields``,
        ``bool_fields``, ``int_fields``, ``float_fields``, ``nvt_fields``,
        ``required_fields``, ``codelijsten``, ``single_row``).

    Raises:
        FileNotFoundError: Als het schema-bestand niet bestaat.
    """
    return {k: v for k, v in _lees_toml(name).items() if isinstance(v, dict)}


def schema_meta(name: str) -> dict:
    """Geef de top-level metadata van een schema (bijv. ``schema_version``)."""
    return {k: v for k, v in _lees_toml(name).items() if not isinstance(v, dict)}


@lru_cache
def _lees_codelijst(name: str) -> pl.DataFrame:
    pad = SCHEMA_DIR / f"{name}.csv"
    if not pad.exists():
        raise FileNotFoundError(f"Codelijst niet gevonden: {pad}")
    return pl.read_csv(pad, infer_schema=False)


def load_codelijst(name: str) -> pl.DataFrame:
    """Laad een codelijst uit ``metadata/{name}.csv``; alle kolommen als tekst.

    Raises:
        FileNotFoundError: Als de codelijst niet bestaat.
    """
    return _lees_codelijst(name).clone()
