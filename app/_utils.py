"""Gedeelde hulpfuncties voor de Streamlit-app (geen bedrijfslogica)."""

import os
import tomllib
from pathlib import Path

import polars as pl

from ho_bekostiging_bestanden.pipeline import DATAMODEL_MAP
from ho_bekostiging_bestanden.star import STAR_TABELLEN

CONFIG_ENV = "HO_APP_CONFIG"
_STANDAARD_CONFIG = Path(__file__).parent / "config.toml"
# Relatieve datapaden gaan uit van de repo-map, niet van de map waarin je
# `streamlit run` start.
REPO_ROOT = Path(__file__).parents[1]


def load_config() -> dict:
    config_path = Path(os.environ.get(CONFIG_ENV, _STANDAARD_CONFIG))
    with config_path.open("rb") as f:
        return tomllib.load(f)


def _datapad(sleutel: str) -> Path:
    pad = Path(load_config()["data"][sleutel])
    return pad if pad.is_absolute() else REPO_ROOT / pad


def raw_dir() -> Path:
    return _datapad("raw")


def prepared_dir() -> Path:
    return _datapad("prepared")


def output_dir() -> Path:
    return _datapad("output")


def datamodel_dir() -> Path:
    return output_dir() / DATAMODEL_MAP


def lees_star(datamodel: Path) -> dict[str, pl.DataFrame] | None:
    """Lees alle star-tabellen; ``None`` als het star schema nog niet bestaat."""
    paden = {naam: datamodel / f"{naam}.parquet" for naam in STAR_TABELLEN}
    if not all(p.exists() for p in paden.values()):
        return None
    return {naam: pl.read_parquet(p) for naam, p in paden.items()}
