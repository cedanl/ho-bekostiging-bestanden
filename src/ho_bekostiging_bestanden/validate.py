"""Kwaliteitscontroles op een ingelezen levering.

De controles houden de verwerking niet tegen: ze leveren een rapport op dat
in de app en in de tabel ``VALIDATIE`` getoond wordt. Alleen een ontbrekend
voorlooprecord is fataal, omdat de levering dan niet te plaatsen is.
"""

import re

import polars as pl

from ho_bekostiging_bestanden.decode import STATUS_SCHEIDING
from ho_bekostiging_bestanden.ingest import MELDINGEN, Bestandsinfo
from ho_bekostiging_bestanden.metadata import load_codelijst, load_schema

VALIDATIE_SCHEMA = {
    "Controle": pl.Utf8,
    "Recordsoort": pl.Utf8,
    "Melding": pl.Utf8,
    "Aantal": pl.Int64,
}
VOORLOOP = "VLP"
SLUIT = "SLR"
_SLR_VELD_RE = re.compile(r"^Aantal([A-Z]{3})records$")


def _melding(controle: str, rs: str, melding: str, aantal: int = 1) -> dict:
    return {
        "Controle": controle,
        "Recordsoort": rs,
        "Melding": melding,
        "Aantal": aantal,
    }


def _inlezen(frames: dict[str, pl.DataFrame]) -> list[dict]:
    meldingen = frames.get(MELDINGEN)
    if meldingen is None or meldingen.is_empty():
        return []
    telling = meldingen.group_by(["Recordsoort", "Melding"], maintain_order=True).len()
    return [
        _melding("Inlezen", r["Recordsoort"], r["Melding"], r["len"])
        for r in telling.iter_rows(named=True)
    ]


def _aantal_records(frames: dict[str, pl.DataFrame]) -> list[dict]:
    slr = frames.get(SLUIT)
    if slr is None or slr.is_empty():
        return [_melding("Aantal records", SLUIT, "Geen sluitrecord (SLR)")]
    uitkomst = []
    for veld in slr.columns:
        match = _SLR_VELD_RE.match(veld)
        if match is None:
            continue
        rs = match.group(1)
        verwacht = slr[veld][0]
        gevonden = frames[rs].height if rs in frames else 0
        if verwacht != gevonden:
            uitkomst.append(
                _melding(
                    "Aantal records", rs, f"SLR meldt {verwacht}, gevonden {gevonden}"
                )
            )
    return uitkomst


def _een_rij(frames: dict[str, pl.DataFrame], schema: dict[str, dict]) -> list[dict]:
    return [
        _melding("Eén rij", rs, f"Verwacht 1 rij, gevonden {frames[rs].height}")
        for rs, spec in schema.items()
        if spec.get("single_row") and rs in frames and frames[rs].height != 1
    ]


def _verplicht(frames: dict[str, pl.DataFrame], schema: dict[str, dict]) -> list[dict]:
    uitkomst = []
    for rs, spec in schema.items():
        if rs not in frames:
            continue
        for veld in spec.get("required_fields", []):
            leeg = frames[rs][veld].null_count()
            if leeg:
                uitkomst.append(_melding("Verplicht veld", rs, f"{veld} is leeg", leeg))
    return uitkomst


def _codelijsten(
    frames: dict[str, pl.DataFrame], schema: dict[str, dict]
) -> list[dict]:
    uitkomst = []
    for rs, spec in schema.items():
        if rs not in frames:
            continue
        for veld, lijst in spec.get("codelijsten", {}).items():
            geldig = load_codelijst(lijst)["Code"].to_list()
            onbekend = (
                frames[rs]
                .select(
                    pl.col(veld)
                    .str.split(STATUS_SCHEIDING)
                    .explode(empty_as_null=True)
                    .alias("c")
                )
                .drop_nulls()
                .filter(~pl.col("c").is_in(geldig))
                .group_by("c", maintain_order=True)
                .len()
                .sort("c")
            )
            uitkomst += [
                _melding(
                    "Codelijst", rs, f"{veld}: onbekende code '{r['c']}'", r["len"]
                )
                for r in onbekend.iter_rows(named=True)
            ]
    return uitkomst


def _bestandsnaam(vlp: pl.DataFrame, info: Bestandsinfo) -> list[dict]:
    uitkomst = []
    brin = vlp["BRIN"][0]
    if brin != info.brin:
        uitkomst.append(
            _melding(
                "Bestandsnaam",
                VOORLOOP,
                f"BRIN in bestandsnaam ({info.brin}) wijkt af van VLP ({brin})",
            )
        )
    if "Bekostigingsjaar" in vlp.columns:
        jaar = vlp["Bekostigingsjaar"][0]
        if jaar != info.bekostigingsjaar:
            uitkomst.append(
                _melding(
                    "Bestandsnaam",
                    VOORLOOP,
                    f"Jaar in bestandsnaam ({info.bekostigingsjaar}) "
                    f"wijkt af van VLP ({jaar})",
                )
            )
    return uitkomst


def valideer(
    frames: dict[str, pl.DataFrame],
    schema_name: str,
    info: Bestandsinfo,
) -> pl.DataFrame:
    """Controleer een gedecodeerde levering en geef de meldingen terug.

    Args:
        frames:      Uitvoer van :func:`decode_frames` (inclusief ``MELDINGEN``).
        schema_name: ``"analyse"`` of ``"hisbek"``.
        info:        Gegevens uit de bestandsnaam.

    Returns:
        DataFrame met kolommen ``VALIDATIE_SCHEMA``; leeg als alles klopt.

    Raises:
        ValueError: Als het voorlooprecord (VLP) ontbreekt.
    """
    if VOORLOOP not in frames or frames[VOORLOOP].is_empty():
        raise ValueError(f"Geen voorlooprecord (VLP) in {info.bestandsnaam}")
    schema = load_schema(schema_name)
    rijen = (
        _inlezen(frames)
        + _aantal_records(frames)
        + _een_rij(frames, schema)
        + _verplicht(frames, schema)
        + _codelijsten(frames, schema)
        + _bestandsnaam(frames[VOORLOOP], info)
    )
    return pl.DataFrame(rijen, schema=VALIDATIE_SCHEMA)
