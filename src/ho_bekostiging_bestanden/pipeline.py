"""Orkestratie van de ingestion-pipeline: ingest > decode > validate > export."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from ho_bekostiging_bestanden.decode import decode_frames
from ho_bekostiging_bestanden.export import OutputFormat, export_frames
from ho_bekostiging_bestanden.ingest import (
    LEVERING,
    MELDINGEN,
    SCHEMA_PER_LEVERING,
    VALIDATIE,
    Bestandsinfo,
    parse_bestandsnaam,
    read_multi_record_csv,
)
from ho_bekostiging_bestanden.metadata import schema_meta
from ho_bekostiging_bestanden.stack import stack_prepared
from ho_bekostiging_bestanden.star import build_star
from ho_bekostiging_bestanden.validate import VOORLOOP, valideer

__all__ = [
    "DATAMODEL_MAP",
    "LEVERING",
    "VALIDATIE",
    "Verwerking",
    "detect_levering",
    "run_pipeline",
    "run_star",
    "verwerk_alles",
    "vind_bestanden",
]

DATAMODEL_MAP = "datamodel"


def detect_levering(path: str | Path) -> str | None:
    """Geef de soort levering (``VLPBEK``/``DEFBEK``/``HISBEK``) of ``None``."""
    info = parse_bestandsnaam(path)
    return info.soort if info else None


def _levering_tabel(
    info: Bestandsinfo, vlp: pl.DataFrame, schema_name: str
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "SoortLevering": [info.soort],
            "Bekostigingsjaar": [info.bekostigingsjaar],
            "DatumAanmaak": [vlp["DatumAanmaak"][0]],
            "BrinOntvanger": [vlp["BRIN"][0]],
            "Bestandsnaam": [info.bestandsnaam],
            "SchemaVersie": [str(schema_meta(schema_name)["schema_version"])],
        },
        schema={
            "SoortLevering": pl.Utf8,
            "Bekostigingsjaar": pl.Int64,
            "DatumAanmaak": pl.Date,
            "BrinOntvanger": pl.Utf8,
            "Bestandsnaam": pl.Utf8,
            "SchemaVersie": pl.Utf8,
        },
    )


def run_pipeline(
    source: str | Path,
    target: str | Path,
    fmt: OutputFormat = "parquet",
) -> dict[str, pl.DataFrame]:
    """Verwerk één ruw analysebestand of HISBEK-bestand naar ``target``.

    Args:
        source: Pad naar het ruwe bestand (``VLPBEK_…``, ``DEFBEK_…``, ``HISBEK_…``).
        target: Doelmap voor de prepared-tabellen.
        fmt:    ``"parquet"`` (standaard) of ``"csv"``.

    Returns:
        Dict van tabelnaam naar DataFrame: de recordsoorten plus ``LEVERING``
        en ``VALIDATIE``.

    Raises:
        ValueError: Als de bestandsnaam niet herkend wordt of de VLP ontbreekt.
    """
    info = parse_bestandsnaam(source)
    if info is None:
        raise ValueError(
            f"Onbekend bestandstype: {Path(source).name!r}. "
            f"Verwacht TTTTTT_JJJJ_EEJJMMDD_99XX.csv met TTTTTT in "
            f"{sorted(SCHEMA_PER_LEVERING)}."
        )
    schema_name = SCHEMA_PER_LEVERING[info.soort]
    frames = decode_frames(read_multi_record_csv(source, schema_name), schema_name)
    rapport = valideer(frames, schema_name, info)
    uitvoer = {rs: df for rs, df in frames.items() if rs != MELDINGEN}
    uitvoer[LEVERING] = _levering_tabel(info, frames[VOORLOOP], schema_name)
    uitvoer[VALIDATIE] = rapport
    export_frames(uitvoer, target, fmt=fmt)
    return uitvoer


def run_star(
    sources: Sequence[Path | str],
    target: str | Path,
) -> dict[str, pl.DataFrame]:
    """Stapel prepared-mappen, bouw het star schema en schrijf het weg.

    Args:
        sources: Mappen met prepared Parquet-bestanden (één per levering).
        target:  Doelmap; het star schema komt in ``<target>/datamodel/``.

    Returns:
        Dict met de star-schema-tabellen.
    """
    star = build_star(stack_prepared(sources))
    export_frames(star, Path(target) / DATAMODEL_MAP)
    return star


@dataclass
class Verwerking:
    """Uitkomst van :func:`verwerk_alles`."""

    prepared_dirs: list[Path] = field(default_factory=list)
    star: dict[str, pl.DataFrame] = field(default_factory=dict)
    validatie: dict[str, pl.DataFrame] = field(default_factory=dict)
    fouten: dict[str, str] = field(default_factory=dict)


def vind_bestanden(raw: Path) -> list[Path]:
    """Alle herkende leveringen onder ``raw`` (recursief, gesorteerd)."""
    return [
        p
        for p in sorted(Path(raw).rglob("*"))
        if p.is_file() and detect_levering(p) is not None
    ]


def verwerk_alles(raw: Path, prepared: Path, output: Path) -> Verwerking:
    """Verwerk alle herkende bestanden in ``raw`` en bouw het star schema.

    Een bestand dat niet verwerkt kan worden (bijv. zonder VLP) komt in
    ``fouten``; de overige bestanden gaan gewoon door.

    Args:
        raw:      Map met ruwe bestanden.
        prepared: Map voor de prepared-tabellen (één submap per bestand).
        output:   Map voor het star schema.

    Returns:
        :class:`Verwerking` met prepared-mappen, star schema, validatie en fouten.
    """
    resultaat = Verwerking()
    for bestand in vind_bestanden(raw):
        doel = Path(prepared) / bestand.stem
        try:
            frames = run_pipeline(bestand, doel)
        except ValueError as fout:
            resultaat.fouten[bestand.name] = str(fout)
            continue
        resultaat.prepared_dirs.append(doel)
        resultaat.validatie[bestand.name] = frames[VALIDATIE]
    resultaat.star = run_star(resultaat.prepared_dirs, output)
    return resultaat
