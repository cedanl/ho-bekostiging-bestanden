"""Gedeelde hulpfuncties voor de Streamlit-app (geen bedrijfslogica)."""

import os
import tomllib
from pathlib import Path
from typing import NamedTuple

import polars as pl
import streamlit as st

from ho_bekostiging_bestanden.kwaliteit import (
    QUALITY_JSON,
    STATUS_FAIL,
    STATUS_WARN,
    lees_status,
)
from ho_bekostiging_bestanden.pipeline import DATAMODEL_MAP
from ho_bekostiging_bestanden.pseudonimisering import SLEUTEL_ENV, laad_sleutel
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


def kwaliteitsbanner() -> None:
    """Toon de kwaliteitsstatus van het laatste star schema, als die niet ok is."""
    pad = output_dir() / QUALITY_JSON
    if not pad.exists():
        return
    status, fouten = lees_status(pad)
    if status == STATUS_FAIL:
        st.error(
            f"Kwaliteitsstatus fail: {fouten} error(s). De cijfers zijn niet "
            f"betrouwbaar; zie {QUALITY_JSON} of verwerk opnieuw op de Home-pagina."
        )
    elif status == STATUS_WARN:
        st.warning(
            f"Kwaliteitsstatus warn: er zijn waarschuwingen; zie {QUALITY_JSON}."
        )


def lees_star(datamodel: Path) -> dict[str, pl.DataFrame] | None:
    """Lees alle star-tabellen; ``None`` als het star schema nog niet bestaat."""
    paden = {naam: datamodel / f"{naam}.parquet" for naam in STAR_TABELLEN}
    if not all(p.exists() for p in paden.values()):
        return None
    return {naam: pl.read_parquet(p) for naam, p in paden.items()}


class Sleutelstatus(NamedTuple):
    """Pseudonimiseringssleutel voor de app, met herkomst of foutmelding."""

    sleutel: bytes | None
    is_demo: bool
    fout: str | None


def pseudonimiseringssleutel() -> Sleutelstatus:
    """Sleutel uit ``EENCIJFERHO_ENCRYPT_KEY``; anders de demo-sleutel uit de config.

    De omgevingsvariabele gaat altijd voor, zodat echte data nooit met de
    openbare demo-sleutel gepseudonimiseerd wordt als die variabele gezet is.
    """
    demo = load_config().get("security", {}).get("demo_sleutel")
    is_demo = not os.environ.get(SLEUTEL_ENV) and bool(demo)
    try:
        return Sleutelstatus(laad_sleutel(demo if is_demo else None), is_demo, None)
    except ValueError as fout:
        return Sleutelstatus(None, is_demo, str(fout))
