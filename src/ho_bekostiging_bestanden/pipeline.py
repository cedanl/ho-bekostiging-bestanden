"""Orkestratie van de ingestion-pipeline: ingest > decode > validate > export."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import get_args

import polars as pl

from ho_bekostiging_bestanden import contracten
from ho_bekostiging_bestanden.decode import decode_frames
from ho_bekostiging_bestanden.export import OutputFormat, export_frames
from ho_bekostiging_bestanden.ingest import (
    EXTENSIE,
    LEVERING,
    MELDINGEN,
    SCHEMA_PER_LEVERING,
    VALIDATIE,
    Bestandsinfo,
    parse_bestandsnaam,
    read_multi_record_csv,
)
from ho_bekostiging_bestanden.kwaliteit import (
    BRON_KOLOM,
    ERNST_ERROR,
    ERNST_KOLOM,
    MELDING_SCHEMA,
    QUALITY_JSON,
    RAPPORT_SCHEMA,
    STAR_BRON,
    STATUS_OK,
    bouw_rapport,
    melding,
    meldingen_frame,
    met_bron,
    poort,
    schrijf_rapport,
    status,
)
from ho_bekostiging_bestanden.metadata import schema_meta
from ho_bekostiging_bestanden.pseudonimisering import (
    laad_sleutel,
    pseudonimiseer_frames,
)
from ho_bekostiging_bestanden.stack import LABEL_COL, stack_prepared
from ho_bekostiging_bestanden.star import build_star
from ho_bekostiging_bestanden.validate import VOORLOOP, valideer

__all__ = [
    "DATAMODEL_MAP",
    "LEVERING",
    "VALIDATIE",
    "Verwerking",
    "detect_levering",
    "onherkende_bestanden",
    "run_pipeline",
    "run_star",
    "verwerk_alles",
    "vind_bestanden",
]

DATAMODEL_MAP = "datamodel"
DUBBEL_MELDING = (
    "Dubbel: een bestand met dezelfde naam ({eerste}) is al verwerkt; overgeslagen."
)
VEROUDERD_MELDING = (
    "Prepared-map zonder ernst per melding (van vóór de kwaliteitspoort); "
    "verwerk het bestand opnieuw."
)


def detect_levering(path: str | Path) -> str | None:
    """Geef de soort levering (``VLPBEK``/``DEFBEK``/``HISBEK``) of ``None``."""
    info = parse_bestandsnaam(path)
    return info.soort if info else None


def _levering_tabel(
    info: Bestandsinfo, vlp: pl.DataFrame, schema_name: str, gepseudonimiseerd: bool
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "SoortLevering": [info.soort],
            "Bekostigingsjaar": [info.bekostigingsjaar],
            "DatumAanmaak": [vlp["DatumAanmaak"][0]],
            "BrinOntvanger": [vlp["BRIN"][0]],
            "Bestandsnaam": [info.bestandsnaam],
            "SchemaVersie": [str(schema_meta(schema_name)["schema_version"])],
            "Gepseudonimiseerd": [gepseudonimiseerd],
        },
        schema={
            "SoortLevering": pl.Utf8,
            "Bekostigingsjaar": pl.Int64,
            "DatumAanmaak": pl.Date,
            "BrinOntvanger": pl.Utf8,
            "Bestandsnaam": pl.Utf8,
            "SchemaVersie": pl.Utf8,
            "Gepseudonimiseerd": pl.Boolean,
        },
    )


def _maak_leeg(target: Path) -> None:
    """Verwijder eerder geëxporteerde tabellen, zodat een recordsoort die in de
    nieuwe versie van het bestand ontbreekt niet blijft hangen."""
    for fmt in get_args(OutputFormat):
        for pad in target.glob(f"*.{fmt}"):
            pad.unlink()


def run_pipeline(
    source: str | Path,
    target: str | Path,
    fmt: OutputFormat = "parquet",
    sleutel: bytes | None = None,
    pseudonimiseer: bool = True,
    fail_on_errors: bool = True,
) -> dict[str, pl.DataFrame]:
    """Verwerk één ruw analysebestand of HISBEK-bestand naar ``target``.

    Args:
        source: Pad naar het ruwe bestand (``VLPBEK_…``, ``DEFBEK_…``, ``HISBEK_…``).
        target: Doelmap voor de prepared-tabellen.
        fmt:    ``"parquet"`` (standaard) of ``"csv"``.
        sleutel: Pseudonimiseringssleutel; standaard uit ``EENCIJFERHO_ENCRYPT_KEY``.
                 BSN en onderwijsnummer worden direct na het decoderen
                 gepseudonimiseerd, gelijk aan 1cijferho.
        pseudonimiseer: Standaard ``True``. Met ``False`` blijven BSN en
                 onderwijsnummer leesbaar en is geen sleutel nodig; de tabel
                 ``LEVERING`` legt vast welke keuze is gemaakt.
        fail_on_errors: Werp :class:`KwaliteitsFout` na het wegschrijven als
                 de levering status ``fail`` heeft.

    Returns:
        Dict van tabelnaam naar DataFrame: de recordsoorten plus ``LEVERING``
        en ``VALIDATIE``.

    Raises:
        ValueError: Als de bestandsnaam niet herkend wordt, de VLP ontbreekt of
                    er geen (geldige) pseudonimiseringssleutel is.
        KwaliteitsFout: Bij status ``fail`` en ``fail_on_errors``; de
                    prepared-uitvoer staat dan al op schijf.
    """
    if pseudonimiseer and sleutel is None:
        sleutel = laad_sleutel()
    info = parse_bestandsnaam(source)
    if info is None:
        raise ValueError(
            f"Onbekend bestandstype: {Path(source).name!r}. "
            f"Verwacht TTTTTT_JJJJ_EEJJMMDD_99XX.csv met TTTTTT in "
            f"{sorted(SCHEMA_PER_LEVERING)}."
        )
    schema_name = SCHEMA_PER_LEVERING[info.soort]
    frames = decode_frames(read_multi_record_csv(source, schema_name), schema_name)
    if pseudonimiseer and sleutel is not None:
        frames = pseudonimiseer_frames(frames, sleutel)
    rapport = valideer(frames, schema_name, info)
    uitvoer = {rs: df for rs, df in frames.items() if rs != MELDINGEN}
    uitvoer[LEVERING] = _levering_tabel(
        info, frames[VOORLOOP], schema_name, pseudonimiseer
    )
    uitvoer[VALIDATIE] = rapport
    _maak_leeg(Path(target))
    export_frames(uitvoer, target, fmt=fmt)
    if fail_on_errors:
        poort(
            met_bron(rapport, Path(source).stem),
            f"zie de tabel {VALIDATIE} in {target}",
        )
    return uitvoer


def _leveringmeldingen(
    sources: Sequence[Path | str], stacked: dict[str, pl.DataFrame]
) -> pl.DataFrame:
    """Validatiemeldingen per levering, plus een error per verouderde map."""
    delen = [pl.DataFrame(schema=RAPPORT_SCHEMA)]
    validatie = stacked.get(VALIDATIE)
    if validatie is not None and ERNST_KOLOM in validatie.columns:
        # Rijen zonder ernst komen uit een verouderde map; die krijgt hieronder
        # één eigen error.
        delen.append(
            validatie.filter(pl.col(ERNST_KOLOM).is_not_null()).select(
                pl.col(LABEL_COL).alias(BRON_KOLOM), *MELDING_SCHEMA
            )
        )
    for map_ in map(Path, sources):
        pad = map_ / f"{VALIDATIE}.parquet"
        if not pad.exists() or ERNST_KOLOM not in pl.read_parquet_schema(pad):
            verouderd = melding(
                "Prepared-map", VALIDATIE, VEROUDERD_MELDING, ERNST_ERROR
            )
            delen.append(met_bron(meldingen_frame([verouderd]), map_.name))
    return pl.concat(delen)


def _star_meldingen(star: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Meldingen van de star-contracten (``contracten.py``)."""
    return met_bron(contracten.controleer_star(star), STAR_BRON)


def _bouw_star(
    sources: Sequence[Path | str], target: str | Path, fouten_toegestaan: bool
) -> tuple[dict[str, pl.DataFrame], pl.DataFrame]:
    """Bouw en schrijf star schema en ``quality.json``; geef star en meldingen."""
    stacked = stack_prepared(sources)
    star = build_star(stacked)
    meldingen = pl.concat([_leveringmeldingen(sources, stacked), _star_meldingen(star)])
    export_frames(star, Path(target) / DATAMODEL_MAP)
    schrijf_rapport(
        bouw_rapport(meldingen, star["dim_levering"], fouten_toegestaan), Path(target)
    )
    return star, meldingen


def run_star(
    sources: Sequence[Path | str],
    target: str | Path,
    fail_on_errors: bool = True,
) -> dict[str, pl.DataFrame]:
    """Stapel prepared-mappen, bouw het star schema en schrijf het weg.

    Args:
        sources: Mappen met prepared Parquet-bestanden (één per levering).
        target:  Doelmap; het star schema komt in ``<target>/datamodel/`` en
                 het kwaliteitsrapport in ``<target>/quality.json``.
        fail_on_errors: Werp :class:`KwaliteitsFout` bij status ``fail``.

    Returns:
        Dict met de star-schema-tabellen.

    Raises:
        KwaliteitsFout: Bij status ``fail`` en ``fail_on_errors``; star schema en
                        ``quality.json`` staan dan al op schijf.
    """
    star, meldingen = _bouw_star(sources, target, not fail_on_errors)
    if fail_on_errors:
        poort(meldingen, f"zie {Path(target) / QUALITY_JSON}")
    return star


@dataclass
class Verwerking:
    """Uitkomst van :func:`verwerk_alles`."""

    prepared_dirs: list[Path] = field(default_factory=list)
    star: dict[str, pl.DataFrame] = field(default_factory=dict)
    fouten: dict[str, str] = field(default_factory=dict)
    status: str = STATUS_OK
    meldingen: pl.DataFrame = field(
        default_factory=lambda: pl.DataFrame(schema=RAPPORT_SCHEMA)
    )


def vind_bestanden(raw: Path) -> list[Path]:
    """Alle herkende leveringen onder ``raw`` (recursief, gesorteerd)."""
    return [
        p
        for p in sorted(Path(raw).rglob("*"))
        if p.is_file() and detect_levering(p) is not None
    ]


def onherkende_bestanden(raw: Path) -> list[Path]:
    """CSV-bestanden onder ``raw`` die niet als levering herkend worden.

    Bijvoorbeeld ``… (1).csv`` na een dubbele download, of een ``_OUD``-bestand.
    """
    return [
        p
        for p in sorted(Path(raw).rglob("*"))
        if p.is_file() and p.suffix.lower() == EXTENSIE and detect_levering(p) is None
    ]


def verwerk_alles(
    raw: Path,
    prepared: Path,
    output: Path,
    sleutel: bytes | None = None,
    pseudonimiseer: bool = True,
) -> Verwerking:
    """Verwerk alle herkende bestanden in ``raw`` en bouw het star schema.

    Een bestand dat niet verwerkt kan worden (bijv. zonder VLP) of dat dubbel
    voorkomt, komt in ``fouten``; de overige bestanden gaan gewoon door.
    Gooit geen :class:`KwaliteitsFout`: ``status`` en ``meldingen`` geven de
    kwaliteit, zodat de meldingen per bestand niet verloren gaan.

    Args:
        raw:      Map met ruwe bestanden.
        prepared: Map voor de prepared-tabellen (één submap per bestand).
        output:   Map voor het star schema.
        sleutel:  Pseudonimiseringssleutel; standaard uit ``EENCIJFERHO_ENCRYPT_KEY``.
        pseudonimiseer: Standaard ``True``; met ``False`` is geen sleutel nodig.

    Returns:
        :class:`Verwerking` met prepared-mappen, star schema, fouten, status en
        meldingen.
    """
    # Eén keer laden: zonder geldige sleutel wordt niets verwerkt (ValueError).
    if pseudonimiseer and sleutel is None:
        sleutel = laad_sleutel()
    resultaat = Verwerking()
    gezien: dict[str, Path] = {}
    for bestand in vind_bestanden(raw):
        stam = bestand.stem.upper()
        if stam in gezien:
            # Zelfde levering twee keer (bijv. ook geüpload): één keer tellen.
            eerste = gezien[stam].relative_to(raw)
            resultaat.fouten[str(bestand.relative_to(raw))] = DUBBEL_MELDING.format(
                eerste=eerste
            )
            continue
        gezien[stam] = bestand
        doel = Path(prepared) / bestand.stem
        try:
            run_pipeline(
                bestand,
                doel,
                sleutel=sleutel,
                pseudonimiseer=pseudonimiseer,
                fail_on_errors=False,
            )
        except ValueError as fout:
            resultaat.fouten[bestand.name] = str(fout)
            continue
        resultaat.prepared_dirs.append(doel)
    resultaat.star, resultaat.meldingen = _bouw_star(
        resultaat.prepared_dirs, output, fouten_toegestaan=False
    )
    resultaat.status = status(resultaat.meldingen)
    return resultaat
