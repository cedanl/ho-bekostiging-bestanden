"""Gedeeld kwaliteitscontract: ernst, status, poort en ``quality.json``.

Namen zijn gelijk aan mbo-bekostiging-bestanden, zodat een gedeelde
kernbibliotheek (#9) later eenvoudig is. Een error zet de status op ``fail``;
de uitvoer wordt dan wel geschreven, maar ``poort`` gooit ``KwaliteitsFout``.
"""

import json
from pathlib import Path
from typing import Any

import polars as pl

from ho_bekostiging_bestanden.stack import LABEL_COL

ERNST_ERROR = "error"
ERNST_WARNING = "warning"
STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
QUALITY_JSON = "quality.json"
STAR_BRON = "star schema"
ERNST_KOLOM = "Ernst"
BRON_KOLOM = "Bron"

MELDING_SCHEMA = {
    "Controle": pl.Utf8,
    "Recordsoort": pl.Utf8,
    "Melding": pl.Utf8,
    "Aantal": pl.Int64,
    ERNST_KOLOM: pl.Utf8,
}
RAPPORT_SCHEMA = {BRON_KOLOM: pl.Utf8, **MELDING_SCHEMA}


class KwaliteitsFout(Exception):
    """De kwaliteitsstatus is ``fail``; de uitvoer staat al op schijf.

    ``meldingen`` bevat de error-meldingen (``RAPPORT_SCHEMA``).
    """

    def __init__(self, bericht: str, meldingen: pl.DataFrame) -> None:
        super().__init__(bericht)
        self.meldingen = meldingen


def melding(
    controle: str, recordsoort: str, tekst: str, ernst: str, aantal: int = 1
) -> dict:
    return {
        "Controle": controle,
        "Recordsoort": recordsoort,
        "Melding": tekst,
        "Aantal": aantal,
        ERNST_KOLOM: ernst,
    }


def meldingen_frame(rijen: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rijen, schema=MELDING_SCHEMA)


def met_bron(meldingen: pl.DataFrame, bron: str) -> pl.DataFrame:
    """Meldingen van één bron (levering of star schema) in ``RAPPORT_SCHEMA``."""
    return meldingen.select(pl.lit(bron).alias(BRON_KOLOM), *MELDING_SCHEMA)


def aantal(meldingen: pl.DataFrame, ernst: str) -> int:
    """Aantal meldingen met deze ernst (niet de som van ``Aantal``)."""
    return meldingen.filter(pl.col(ERNST_KOLOM) == ernst).height


def status(meldingen: pl.DataFrame) -> str:
    if aantal(meldingen, ERNST_ERROR):
        return STATUS_FAIL
    if aantal(meldingen, ERNST_WARNING):
        return STATUS_WARN
    return STATUS_OK


def poort(meldingen: pl.DataFrame, verwijzing: str) -> None:
    """Gooi :class:`KwaliteitsFout` als de status ``fail`` is."""
    if status(meldingen) != STATUS_FAIL:
        return
    fouten = meldingen.filter(pl.col(ERNST_KOLOM) == ERNST_ERROR)
    raise KwaliteitsFout(
        f"Kwaliteitsstatus {STATUS_FAIL}: {fouten.height} error(s); {verwijzing}.",
        fouten,
    )


def _als_lijst(meldingen: pl.DataFrame) -> list[dict[str, Any]]:
    return [
        {kolom.lower(): waarde for kolom, waarde in rij.items()}
        for rij in meldingen.select(*MELDING_SCHEMA).iter_rows(named=True)
    ]


def _onderdeel(meldingen: pl.DataFrame, bron: str) -> dict[str, Any]:
    eigen = meldingen.filter(pl.col(BRON_KOLOM) == bron)
    return {"status": status(eigen), "meldingen": _als_lijst(eigen)}


def bouw_rapport(
    meldingen: pl.DataFrame, dim_levering: pl.DataFrame, fouten_toegestaan: bool
) -> dict[str, Any]:
    """Inhoud van ``quality.json``: status, totalen, per levering en star.

    Args:
        meldingen:         Alle meldingen (``RAPPORT_SCHEMA``).
        dim_levering:      Levert de leveringslabels (kolom ``LABEL_COL``).
        fouten_toegestaan: Of de aanroeper een ``fail`` toestaat.
    """
    labels = dim_levering[LABEL_COL].to_list()
    # Een verouderde prepared-map kan meldingen hebben zonder rij in dim_levering.
    labels += sorted(set(meldingen[BRON_KOLOM].to_list()) - set(labels) - {STAR_BRON})
    return {
        "status": status(meldingen),
        "fouten_toegestaan": fouten_toegestaan,
        "total_errors": aantal(meldingen, ERNST_ERROR),
        "total_warnings": aantal(meldingen, ERNST_WARNING),
        "leveringen": [
            {"levering": label, **_onderdeel(meldingen, label)} for label in labels
        ],
        "star": _onderdeel(meldingen, STAR_BRON),
    }


def schrijf_rapport(rapport: dict[str, Any], map_: Path) -> Path:
    """Schrijf ``quality.json`` (UTF-8) in ``map_`` en geef het pad terug."""
    map_.mkdir(parents=True, exist_ok=True)
    pad = map_ / QUALITY_JSON
    pad.write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return pad


def lees_status(pad: Path | str) -> tuple[str, int]:
    """``(status, aantal errors)`` uit een geschreven ``quality.json``."""
    rapport = json.loads(Path(pad).read_text(encoding="utf-8"))
    return rapport["status"], rapport["total_errors"]
