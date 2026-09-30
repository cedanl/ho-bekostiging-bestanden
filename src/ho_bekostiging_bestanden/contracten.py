"""Contracten op het star schema: uniciteit per grain, lege sleutels, koppelingen.

Los van de bouw in ``star.py`` (zoals ``contracts.py`` in
mbo-bekostiging-bestanden). Grain en koppelingen zijn declaratief; een nieuwe
star-tabel voeg je hier toe, niet in een if-keten.

Publieke API:
    controleer_star(star) -> pl.DataFrame  (MELDING_SCHEMA)
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import polars as pl

from ho_bekostiging_bestanden.kwaliteit import ERNST_ERROR, melding, meldingen_frame
from ho_bekostiging_bestanden.stack import LABEL_COL
from ho_bekostiging_bestanden.star import FEIT_ID, PERSOON_ID

Star = dict[str, pl.DataFrame]
# (star-tabel, meldingstekst, aantal)
Bevinding = tuple[str, str, int]

GRAIN: dict[str, list[str]] = {
    "dim_levering": [LABEL_COL],
    "dim_persoon": [PERSOON_ID],
    "dim_instelling": ["BRIN"],
    "dim_opleiding": ["Opleidingscode"],
    "dim_status": ["Code"],
    "fact_deelname": [FEIT_ID],
    "fact_resultaat": [FEIT_ID],
    "fact_status": [FEIT_ID, "Code"],
    "fact_loopbaan": [LABEL_COL, PERSOON_ID],
}


@dataclass(frozen=True)
class Koppeling:
    """Elke niet-lege ``kolom`` in ``feit`` bestaat in dezelfde kolom van een doel."""

    feit: str
    kolom: str
    doelen: tuple[str, ...]


_DEELNAME_RESULTAAT = ("fact_deelname", "fact_resultaat")
_FEITEN = (*_DEELNAME_RESULTAAT, "fact_status", "fact_loopbaan")

KOPPELINGEN: tuple[Koppeling, ...] = (
    *(Koppeling(f, LABEL_COL, ("dim_levering",)) for f in _FEITEN),
    *(
        Koppeling(f, PERSOON_ID, ("dim_persoon",))
        for f in (*_DEELNAME_RESULTAAT, "fact_loopbaan")
    ),
    *(Koppeling(f, "BRIN", ("dim_instelling",)) for f in _DEELNAME_RESULTAAT),
    *(Koppeling(f, "Opleidingscode", ("dim_opleiding",)) for f in _DEELNAME_RESULTAAT),
    Koppeling("fact_status", "Code", ("dim_status",)),
    Koppeling("fact_status", FEIT_ID, _DEELNAME_RESULTAAT),
)


def _dubbel(star: Star) -> Iterator[Bevinding]:
    for tabel, sleutel in GRAIN.items():
        n = int(star[tabel].select(sleutel).is_duplicated().sum())
        if n:
            yield tabel, f"{n} rijen met een dubbele sleutel ({', '.join(sleutel)})", n


def _sleutelkolommen(tabel: str) -> list[str]:
    koppel = [k.kolom for k in KOPPELINGEN if k.feit == tabel]
    return list(dict.fromkeys([*GRAIN[tabel], *koppel]))


def _leeg(star: Star) -> Iterator[Bevinding]:
    for tabel in GRAIN:
        for kolom in _sleutelkolommen(tabel):
            n = star[tabel][kolom].null_count()
            if n:
                yield tabel, f"{kolom} is leeg", n


def _wees(star: Star) -> Iterator[Bevinding]:
    for k in KOPPELINGEN:
        bekend = pl.concat([star[d][k.kolom] for d in k.doelen]).implode()
        kolom = pl.col(k.kolom)
        n = star[k.feit].filter(kolom.is_not_null() & ~kolom.is_in(bekend)).height
        if n:
            doelen = " / ".join(k.doelen)
            yield k.feit, f"{n} waarden van {k.kolom} ontbreken in {doelen}", n


@dataclass(frozen=True)
class Controle:
    naam: str
    ernst: str
    functie: Callable[[Star], Iterator[Bevinding]]


CONTROLES: tuple[Controle, ...] = (
    Controle("Uniciteit", ERNST_ERROR, _dubbel),
    Controle("Lege sleutel", ERNST_ERROR, _leeg),
    Controle("Koppeling", ERNST_ERROR, _wees),
)


def controleer_star(star: Star) -> pl.DataFrame:
    """Loop het register door; één melding per bevinding (``MELDING_SCHEMA``)."""
    return meldingen_frame(
        [
            melding(c.naam, tabel, tekst, c.ernst, n)
            for c in CONTROLES
            for tabel, tekst, n in c.functie(star)
        ]
    )
