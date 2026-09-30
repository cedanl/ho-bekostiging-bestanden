"""Indicatoren voor het dashboard, berekend op het star schema.

Pure functies zonder Streamlit, zodat ze testbaar zijn en de app alleen hoeft
te tonen. Alle functies werken alleen met de eigen instelling (``EigenInstelling``)
en geven een leeg, correct gevormd frame als de benodigde levering ontbreekt.
"""

import polars as pl

from ho_bekostiging_bestanden.decode import STATUS_SCHEIDING, STATUS_VELD
from ho_bekostiging_bestanden.stack import LABEL_COL
from ho_bekostiging_bestanden.star import FEIT_ID, PERSOON_ID

VOORLOPIG = "VLPBEK"
DEFINITIEF = "DEFBEK"
HISTORISCH = "HISBEK"
# Deelnames met status mv vallen buiten de beoordeling (PvE §17.5). [Te checken]
BUITEN_BEOORDELING = "mv"
TRECHTER_STAPPEN = ("In bestand", "Beoordeeld", "Bekostigd")
FEIT_BRON = {"fact_deelname": "deelname", "fact_resultaat": "resultaat"}
DEELNAME_SLEUTEL = ["Bekostigingsjaar", "BRIN", "Inschrijvingvolgnummer", PERSOON_ID]

_REDENEN_SCHEMA = {
    "Groep": pl.Utf8,
    "Code": pl.Utf8,
    "Omschrijving": pl.Utf8,
    "Aantal": pl.UInt32,
}
_VERSCHIL_SCHEMA = {
    "Bekostigingsjaar": pl.Int64,
    "Voorlopig": pl.Utf8,
    "Definitief": pl.Utf8,
    "Aantal": pl.UInt32,
}


def heeft_soort(star: dict[str, pl.DataFrame], soort: str) -> bool:
    """Is er minstens één levering van deze soort (VLPBEK/DEFBEK/HISBEK)?"""
    return soort in star["dim_levering"]["SoortLevering"].to_list()


def actuele_leveringen(star: dict[str, pl.DataFrame], soort: str) -> list[str]:
    """Per bekostigingsjaar het label van de nieuwste levering van ``soort``."""
    return (
        star["dim_levering"]
        .filter(pl.col("SoortLevering") == soort)
        .sort("DatumAanmaak", descending=True)
        .unique("Bekostigingsjaar", keep="first")
        .sort("Bekostigingsjaar")[LABEL_COL]
        .to_list()
    )


def vergelijkbare_jaren(star: dict[str, pl.DataFrame]) -> list[int]:
    """Bekostigingsjaren waarvoor zowel een VLPBEK als een DEFBEK is verwerkt."""

    def jaren(soort: str) -> set[int]:
        leveringen = actuele_leveringen(star, soort)
        dim = star["dim_levering"].filter(pl.col(LABEL_COL).is_in(leveringen))
        return set(dim["Bekostigingsjaar"].drop_nulls().to_list())

    return sorted(jaren(VOORLOPIG) & jaren(DEFINITIEF))


def feiten(
    star: dict[str, pl.DataFrame],
    feit: str,
    leveringen: list[str],
    niveaus: list[str] | None = None,
) -> pl.DataFrame:
    """Feitrijen van de eigen instelling voor de gekozen leveringen.

    Args:
        star:       Uitvoer van :func:`build_star`.
        feit:       ``"fact_deelname"`` of ``"fact_resultaat"``.
        leveringen: Labels uit ``dim_levering.levering``.
        niveaus:    Optioneel filter op ``Opleidingsniveau``.

    Returns:
        Feitrijen met extra kolommen ``SoortLevering``, ``Opleidingsniveau``
        en ``Beoordeeld``.
    """
    eigen = star["dim_instelling"].filter(pl.col("EigenInstelling")).select("BRIN")
    df = (
        star[feit]
        .filter(pl.col(LABEL_COL).is_in(leveringen))
        .join(eigen, on="BRIN", how="semi")
        .join(
            star["dim_levering"].select(LABEL_COL, "SoortLevering"),
            on=LABEL_COL,
            how="left",
        )
        .join(
            star["dim_opleiding"].select("Opleidingscode", "Opleidingsniveau"),
            on="Opleidingscode",
            how="left",
        )
        .with_columns(
            pl.col(STATUS_VELD)
            .str.split(STATUS_SCHEIDING)
            .list.contains(BUITEN_BEOORDELING)
            .not_()
            .fill_null(True)
            .alias("Beoordeeld")
        )
    )
    if niveaus:
        df = df.filter(pl.col("Opleidingsniveau").is_in(niveaus))
    return df


def trechter(df: pl.DataFrame) -> pl.DataFrame:
    """Aantallen per stap: in bestand → beoordeeld → bekostigd."""
    beoordeeld = df.filter(pl.col("Beoordeeld"))
    aantallen = [
        df.height,
        beoordeeld.height,
        beoordeeld.filter(pl.col("Bekostigingsindicatie")).height,
    ]
    return pl.DataFrame(
        {"Stap": list(TRECHTER_STAPPEN), "Aantal": aantallen},
        schema={"Stap": pl.Utf8, "Aantal": pl.Int64},
    )


def redenen_niet_bekostigd(
    df: pl.DataFrame, star: dict[str, pl.DataFrame]
) -> pl.DataFrame:
    """Aantal niet-bekostigde, beoordeelde rijen per statuscode en groep."""
    niet = df.filter(pl.col("Beoordeeld") & ~pl.col("Bekostigingsindicatie")).select(
        FEIT_ID
    )
    if niet.is_empty():
        return pl.DataFrame(schema=_REDENEN_SCHEMA)
    return (
        star["fact_status"]
        .join(niet, on=FEIT_ID, how="semi")
        .join(star["dim_status"].filter(~pl.col("Bekostigd")), on="Code", how="inner")
        .group_by("Groep", "Code", "Omschrijving")
        .len("Aantal")
        .sort(["Aantal", "Code"], descending=[True, False])
        .select(list(_REDENEN_SCHEMA))
    )


def per_opleiding(df: pl.DataFrame) -> pl.DataFrame:
    """Per opleiding: aantal beoordeeld, aantal bekostigd en het aandeel."""
    return (
        df.filter(pl.col("Beoordeeld"))
        .group_by("Opleidingscode", "Opleidingsniveau")
        .agg(
            pl.len().cast(pl.Int64).alias("Totaal"),
            pl.col("Bekostigingsindicatie").sum().cast(pl.Int64).alias("Bekostigd"),
        )
        .with_columns(
            (pl.col("Bekostigd") / pl.col("Totaal")).alias("AandeelBekostigd")
        )
        .sort("Opleidingscode")
    )


def _status_per_deelname(star: dict[str, pl.DataFrame], soort: str) -> pl.DataFrame:
    df = feiten(star, "fact_deelname", actuele_leveringen(star, soort))
    return df.select(*DEELNAME_SLEUTEL, pl.col(STATUS_VELD).alias(soort))


def voorlopig_vs_definitief(star: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Deelnames waarvan de status tussen voorlopig en definitief veranderde."""
    if not vergelijkbare_jaren(star):
        return pl.DataFrame(schema=_VERSCHIL_SCHEMA)
    return (
        _status_per_deelname(star, VOORLOPIG)
        .join(_status_per_deelname(star, DEFINITIEF), on=DEELNAME_SLEUTEL, how="inner")
        .filter(pl.col(VOORLOPIG).ne_missing(pl.col(DEFINITIEF)))
        .rename({VOORLOPIG: "Voorlopig", DEFINITIEF: "Definitief"})
        .group_by("Bekostigingsjaar", "Voorlopig", "Definitief")
        .len("Aantal")
        .sort(["Bekostigingsjaar", "Aantal"], descending=[False, True])
        .select(list(_VERSCHIL_SCHEMA))
    )


def historie(star: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Per bekostigingsjaar en bron: totaal en bekostigd, uit de HISBEK-levering."""
    leveringen = actuele_leveringen(star, HISTORISCH)
    delen = [
        feiten(star, feit, leveringen).select(
            "Bekostigingsjaar", pl.lit(bron).alias("Bron"), "Bekostigingsindicatie"
        )
        for feit, bron in FEIT_BRON.items()
    ]
    return (
        pl.concat(delen)
        .group_by("Bekostigingsjaar", "Bron")
        .agg(
            pl.len().cast(pl.Int64).alias("Totaal"),
            pl.col("Bekostigingsindicatie").sum().cast(pl.Int64).alias("Bekostigd"),
        )
        .sort("Bekostigingsjaar", "Bron")
    )
