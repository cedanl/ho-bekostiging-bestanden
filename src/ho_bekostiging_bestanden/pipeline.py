"""Orkestratie van de ingestion-pipeline: ingest > decode > validate > export."""

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
from ho_bekostiging_bestanden.validate import VOORLOOP, valideer

__all__ = ["LEVERING", "VALIDATIE", "detect_levering", "run_pipeline"]


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
