"""Dimensionaal model (star schema) uit de gestapelde prepared-tabellen.

Vijf dimensies (levering, persoon, instelling, opleiding, status) en vier
feittabellen (deelname, resultaat, status-brug, loopbaan). Kolommen en typen
worden afgeleid uit de schema-TOML's, zodat ontbrekende leveringen (bijv. geen
HISBEK) lege maar correct gevormde tabellen opleveren.

Publieke API:
    build_star(stacked) -> dict[str, pl.DataFrame]
"""

import polars as pl

from ho_bekostiging_bestanden.decode import STATUS_SCHEIDING, STATUS_VELD
from ho_bekostiging_bestanden.ingest import LEVERING, SCHEMA_PER_LEVERING
from ho_bekostiging_bestanden.kwaliteit import SHA256_KOLOM
from ho_bekostiging_bestanden.metadata import load_codelijst, load_schema
from ho_bekostiging_bestanden.stack import LABEL_COL

PERSOON_ID = "_persoon_id"
FEIT_ID = "_feit_id"
DEELNAME_BRONNEN = ("BRD", "HRD")
RESULTAAT_BRONNEN = ("BRR", "HRR")
LOOPBAAN_BRON = "BLB"
PERSOON_VELDEN = ["Burgerservicenummer", "Onderwijsnummer"]
OPLEIDING_VELDEN = [
    "Opleidingsniveau",
    "OpleidingOnderdeel",
    "IndicatieSectorLG",
    "IndicatieAcademischZiekenhuis",
]
STATUS_CODELIJST = "bekostigingstatus"
BEKOSTIGD_JA = "J"
ONBEKENDE_STATUS = {
    "Omschrijving": "Onbekende code (niet in de PvE)",
    "Groep": "Onbekend",
}

DIM_LEVERING_SCHEMA = {
    LABEL_COL: pl.Utf8,
    "SoortLevering": pl.Utf8,
    "Bekostigingsjaar": pl.Int64,
    "DatumAanmaak": pl.Date,
    "BrinOntvanger": pl.Utf8,
    "Bestandsnaam": pl.Utf8,
    SHA256_KOLOM: pl.Utf8,
    "Gepseudonimiseerd": pl.Boolean,
}

STAR_TABELLEN = (
    "dim_levering",
    "dim_persoon",
    "dim_instelling",
    "dim_opleiding",
    "dim_status",
    "fact_deelname",
    "fact_resultaat",
    "fact_status",
    "fact_loopbaan",
)

_TYPE_PER_SLEUTEL = {
    "date_fields": pl.Date,
    "bool_fields": pl.Boolean,
    "int_fields": pl.Int64,
    "float_fields": pl.Float64,
}


def _veldtypen(rs: str) -> dict[str, type[pl.DataType]]:
    """Kolomtypen van een recordsoort, afgeleid uit de schema-TOML."""
    for schema_naam in dict.fromkeys(SCHEMA_PER_LEVERING.values()):
        spec = load_schema(schema_naam).get(rs)
        if spec is None:
            continue
        typen: dict[str, type[pl.DataType]] = {veld: pl.Utf8 for veld in spec["fields"]}
        for sleutel, dtype in _TYPE_PER_SLEUTEL.items():
            typen.update({veld: dtype for veld in spec.get(sleutel, [])})
        return typen
    raise KeyError(f"Recordsoort {rs} staat in geen enkel schema")


def _met_template(
    stacked: dict[str, pl.DataFrame], bronnen: tuple[str, ...]
) -> pl.DataFrame:
    """Zet de bronnen onder elkaar, met gegarandeerd alle schemakolommen."""
    template: dict[str, type[pl.DataType]] = {LABEL_COL: pl.Utf8}
    for rs in bronnen:
        template.update(_veldtypen(rs))
    delen = [pl.DataFrame(schema=template)]
    delen += [
        stacked[rs] for rs in bronnen if rs in stacked and not stacked[rs].is_empty()
    ]
    return pl.concat(delen, how="diagonal_relaxed")


def _persoon_id() -> pl.Expr:
    return pl.coalesce(PERSOON_VELDEN).alias(PERSOON_ID)


def _nieuwste_eerst(
    df: pl.DataFrame, dim_levering: pl.DataFrame, sleutel: str, velden: list[str]
) -> pl.DataFrame:
    """Per sleutel de eerste niet-lege waarde per veld, nieuwste levering eerst."""
    aanmaak = dim_levering.select(LABEL_COL, "DatumAanmaak")
    return (
        df.filter(pl.col(sleutel).is_not_null())
        .join(aanmaak, on=LABEL_COL, how="left")
        .sort("DatumAanmaak", descending=True, nulls_last=True)
        .group_by(sleutel, maintain_order=True)
        .agg(pl.col(v).drop_nulls().first() for v in velden)
        .sort(sleutel)
    )


def _dim_levering(stacked: dict[str, pl.DataFrame]) -> pl.DataFrame:
    delen = [pl.DataFrame(schema=DIM_LEVERING_SCHEMA)]
    if LEVERING in stacked:
        levering = stacked[LEVERING]
        # Oudere prepared-mappen kennen niet alle kolommen (bijv. Gepseudonimiseerd).
        ontbrekend = [
            pl.lit(None, dtype=dtype).alias(kolom)
            for kolom, dtype in DIM_LEVERING_SCHEMA.items()
            if kolom not in levering.columns
        ]
        delen.append(
            levering.with_columns(ontbrekend).select(list(DIM_LEVERING_SCHEMA))
        )
    # Niet ontdubbelen: stack_prepared weigert dubbele labels, en het
    # grain-contract in contracten.py bewaakt één rij per levering.
    return pl.concat(delen, how="vertical_relaxed").sort(LABEL_COL)


def _feiten(
    stacked: dict[str, pl.DataFrame],
    bronnen: tuple[str, ...],
    prefix: str,
    dim_levering: pl.DataFrame,
) -> pl.DataFrame:
    """Feittabel: BRD+HRD of BRR+HRR, met ``_feit_id`` en bekostigingsjaar.

    BRD/BRR hebben geen eigen bekostigingsjaar; dat komt uit de levering.
    Persoons- en opleidingsattributen verhuizen naar de dimensies.
    """
    jaar = dim_levering.select(LABEL_COL, pl.col("Bekostigingsjaar").alias("_jaar"))
    df = (
        _met_template(stacked, bronnen)
        .join(jaar, on=LABEL_COL, how="left", maintain_order="left")
        .with_columns(
            pl.coalesce("Bekostigingsjaar", "_jaar").alias("Bekostigingsjaar"),
            _persoon_id(),
        )
        .drop("_jaar", *PERSOON_VELDEN, *OPLEIDING_VELDEN)
        # Rijnummer per levering: stabiel als er een levering bijkomt.
        .with_columns(pl.int_range(pl.len()).over(LABEL_COL).alias("_rij"))
        .with_columns(
            pl.concat_str(
                [pl.lit(prefix), pl.col(LABEL_COL), pl.col("_rij").cast(pl.Utf8)],
                separator=":",
            ).alias(FEIT_ID)
        )
        .drop("_rij")
    )
    eerst = [FEIT_ID, LABEL_COL, PERSOON_ID]
    return df.select(eerst + [c for c in df.columns if c not in eerst])


def _graadvelden() -> list[str]:
    return [v for v, t in _veldtypen(LOOPBAAN_BRON).items() if t == pl.Date]


def _fact_loopbaan(stacked: dict[str, pl.DataFrame]) -> pl.DataFrame:
    df = _met_template(stacked, (LOOPBAAN_BRON,)).with_columns(_persoon_id())
    df = df.drop("Recordsoort", *PERSOON_VELDEN, *_graadvelden())
    eerst = [LABEL_COL, PERSOON_ID]
    return df.select(eerst + [c for c in df.columns if c not in eerst])


def _dim_persoon(
    stacked: dict[str, pl.DataFrame], dim_levering: pl.DataFrame
) -> pl.DataFrame:
    graad = _graadvelden()
    kolommen = (LABEL_COL, *PERSOON_VELDEN, *graad)
    delen = []
    for rs in (LOOPBAAN_BRON, *DEELNAME_BRONNEN, *RESULTAAT_BRONNEN):
        df = _met_template(stacked, (rs,))
        delen.append(df.select([c for c in kolommen if c in df.columns]))
    bron = pl.concat(delen, how="diagonal_relaxed").with_columns(_persoon_id())
    return _nieuwste_eerst(bron, dim_levering, PERSOON_ID, [*PERSOON_VELDEN, *graad])


def _dim_opleiding(
    stacked: dict[str, pl.DataFrame], dim_levering: pl.DataFrame
) -> pl.DataFrame:
    velden = [LABEL_COL, "Opleidingscode", *OPLEIDING_VELDEN]
    bron = pl.concat(
        [
            _met_template(stacked, (rs,)).select(velden)
            for rs in (*DEELNAME_BRONNEN, *RESULTAAT_BRONNEN)
        ],
        how="vertical_relaxed",
    )
    return _nieuwste_eerst(bron, dim_levering, "Opleidingscode", OPLEIDING_VELDEN)


def _dim_instelling(
    deelname: pl.DataFrame, resultaat: pl.DataFrame, dim_levering: pl.DataFrame
) -> pl.DataFrame:
    ontvangers = dim_levering["BrinOntvanger"].drop_nulls()
    brins = pl.concat(
        [
            deelname.select("BRIN"),
            resultaat.select("BRIN"),
            dim_levering.select(pl.col("BrinOntvanger").alias("BRIN")),
        ]
    )
    return (
        brins.drop_nulls()
        .unique()
        .sort("BRIN")
        .with_columns(
            pl.col("BRIN").is_in(ontvangers.implode()).alias("EigenInstelling")
        )
    )


def _fact_status(deelname: pl.DataFrame, resultaat: pl.DataFrame) -> pl.DataFrame:
    delen = [
        feit.select(
            FEIT_ID,
            LABEL_COL,
            pl.lit(bron).alias("Bron"),
            pl.col(STATUS_VELD).str.split(STATUS_SCHEIDING).alias("Code"),
        )
        for feit, bron in ((deelname, "deelname"), (resultaat, "resultaat"))
    ]
    return (
        pl.concat(delen)
        .explode("Code", empty_as_null=True)
        .filter(pl.col("Code").is_not_null())
    )


def _dim_status(fact_status: pl.DataFrame) -> pl.DataFrame:
    """Codelijst plus eventuele codes uit de data die niet in de PvE staan."""
    codelijst = load_codelijst(STATUS_CODELIJST).with_columns(
        (pl.col("Bekostigd") == BEKOSTIGD_JA).alias("Bekostigd")
    )
    onbekend = (
        fact_status.select("Code")
        .unique()
        .filter(~pl.col("Code").is_in(codelijst["Code"].implode()))
        .with_columns(
            *[pl.lit(v).alias(k) for k, v in ONBEKENDE_STATUS.items()],
            pl.lit(False).alias("Bekostigd"),
        )
    )
    return pl.concat([codelijst, onbekend.select(codelijst.columns)]).sort("Code")


def _controleer_pseudonimisering(dim_levering: pl.DataFrame) -> None:
    """Weiger een mix van gepseudonimiseerde en leesbare leveringen.

    Een pseudoniem en een leesbaar BSN van dezelfde student koppelen niet; een
    gemengd star schema zou studenten stil dubbel tellen.
    """
    keuzes = dim_levering["Gepseudonimiseerd"].drop_nulls().unique()
    if keuzes.len() > 1:
        raise ValueError(
            "De leveringen zijn deels wel en deels niet gepseudonimiseerd. "
            "Verwerk ze allemaal met dezelfde keuze voor pseudonimisering."
        )


def build_star(stacked: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    """Bouw het star schema uit de uitvoer van :func:`stack_prepared`.

    Args:
        stacked: Tabelnaam → gestapelde DataFrame (recordsoorten en ``LEVERING``).

    Returns:
        Dict met de tabellen uit ``STAR_TABELLEN``, in die volgorde. Tabellen
        waarvoor geen bron is, zijn leeg maar hebben hun vaste kolommen.

    Raises:
        ValueError: Als gepseudonimiseerde en leesbare leveringen gemengd zijn.
    """
    dim_levering = _dim_levering(stacked)
    _controleer_pseudonimisering(dim_levering)
    deelname = _feiten(stacked, DEELNAME_BRONNEN, "D", dim_levering)
    resultaat = _feiten(stacked, RESULTAAT_BRONNEN, "R", dim_levering)
    status = _fact_status(deelname, resultaat)
    tabellen = {
        "dim_levering": dim_levering,
        "dim_persoon": _dim_persoon(stacked, dim_levering),
        "dim_instelling": _dim_instelling(deelname, resultaat, dim_levering),
        "dim_opleiding": _dim_opleiding(stacked, dim_levering),
        "dim_status": _dim_status(status),
        "fact_deelname": deelname,
        "fact_resultaat": resultaat,
        "fact_status": status,
        "fact_loopbaan": _fact_loopbaan(stacked),
    }
    return {naam: tabellen[naam] for naam in STAR_TABELLEN}
