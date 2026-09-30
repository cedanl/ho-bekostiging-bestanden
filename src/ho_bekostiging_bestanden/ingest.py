"""Inlezen van ruwe HO-bekostigingsbestanden (analysebestand en HISBEK)."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import polars as pl

from ho_bekostiging_bestanden.metadata import load_schema

# Soort levering (eerste deel van de bestandsnaam) → schemanaam in metadata/.
SCHEMA_PER_LEVERING: dict[str, str] = {
    "VLPBEK": "analyse",
    "DEFBEK": "analyse",
    "HISBEK": "hisbek",
}

SEPARATOR = "|"
EXTENSIE = ".csv"

# Namen van de extra tabellen naast de recordsoorten. MELDINGEN vult ingest
# zelf; LEVERING en VALIDATIE vult de pipeline. Ze staan hier centraal zodat
# pipeline en star ze kunnen delen zonder circulaire import.
MELDINGEN = "_MELDINGEN"
LEVERING = "LEVERING"
VALIDATIE = "VALIDATIE"

# TTTTTT_JJJJ_EEJJMMDD_99XX — de PvE noteert "TTTTTT_ 1234", dus een spatie
# na de eerste underscore wordt getolereerd.
_BESTANDSNAAM_RE = re.compile(
    rf"^({'|'.join(SCHEMA_PER_LEVERING)})_ ?(\d{{4}})_(\d{{8}})_(\d{{2}}[A-Z]{{2}})$"
)

_MELDING_SCHEMA = {"Regelnummer": pl.Int64, "Recordsoort": pl.Utf8, "Melding": pl.Utf8}


@dataclass(frozen=True)
class Bestandsinfo:
    """Gegevens die uit de bestandsnaam van een levering af te leiden zijn."""

    soort: str
    bekostigingsjaar: int
    datum_aanmaak: date
    brin: str
    bestandsnaam: str


def parse_bestandsnaam(path: str | Path) -> Bestandsinfo | None:
    """Ontleed ``TTTTTT_JJJJ_EEJJMMDD_99XX.CSV``; ``None`` als het niet past.

    Hoofd- en kleine letters maken niet uit. Bij HISBEK is het jaar het
    laatste bekostigingsjaar in het bestand.
    """
    path = Path(path)
    if path.suffix.lower() != EXTENSIE:
        return None
    match = _BESTANDSNAAM_RE.match(path.stem.upper())
    if match is None:
        return None
    soort, jaar, datum, brin = match.groups()
    try:
        datum_aanmaak = datetime.strptime(datum, "%Y%m%d").date()
    except ValueError:
        return None
    return Bestandsinfo(soort, int(jaar), datum_aanmaak, brin, path.name)


def _lees_regels(path: Path) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")
    return content.splitlines()


def read_multi_record_csv(
    path: str | Path,
    schema_name: str,
) -> dict[str, pl.DataFrame]:
    """Lees een multi-record ``|``-bestand in en splits per recordsoort.

    Elke regel wordt afgekapt of aangevuld tot het aantal velden in het
    schema; DUO vult regels op met lege velden. Afwijkingen (onbekende
    recordsoort, gevulde velden voorbij het schema) komen in het frame
    ``MELDINGEN``.

    Args:
        path:        Pad naar het bronbestand.
        schema_name: Naam van het schema (``"analyse"`` of ``"hisbek"``).

    Returns:
        Dict van recordsoort naar DataFrame (alle kolommen tekst) plus
        ``MELDINGEN``. Recordsoorten zonder regels ontbreken.

    Raises:
        FileNotFoundError: Als het bronbestand of het schema niet bestaat.
        ValueError:        Als het bestand leeg is.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Bronbestand niet gevonden: {path}")

    schema = {rs: spec["fields"] for rs, spec in load_schema(schema_name).items()}
    regels = _lees_regels(path)
    if not any(r.strip() for r in regels):
        raise ValueError(f"Leeg bestand: {path}")

    rijen: dict[str, list[list[str]]] = {rs: [] for rs in schema}
    meldingen: list[dict] = []
    for regelnummer, regel in enumerate(regels, start=1):
        if not regel.strip():
            continue
        velden = regel.split(SEPARATOR)
        rs = velden[0]
        if rs not in schema:
            meldingen.append(
                {
                    "Regelnummer": regelnummer,
                    "Recordsoort": rs,
                    "Melding": "Onbekende recordsoort",
                }
            )
            continue
        n = len(schema[rs])
        extra = [v for v in velden[n:] if v.strip()]
        if extra:
            meldingen.append(
                {
                    "Regelnummer": regelnummer,
                    "Recordsoort": rs,
                    "Melding": f"{len(extra)} meer gevulde velden dan het schema ({n})",
                }
            )
        rijen[rs].append((velden + [""] * n)[:n])

    result = {
        rs: pl.DataFrame(
            {col: [r[i] for r in rs_rijen] for i, col in enumerate(schema[rs])},
            schema={col: pl.Utf8 for col in schema[rs]},
        )
        for rs, rs_rijen in rijen.items()
        if rs_rijen
    }
    result[MELDINGEN] = pl.DataFrame(meldingen, schema=_MELDING_SCHEMA)
    return result
