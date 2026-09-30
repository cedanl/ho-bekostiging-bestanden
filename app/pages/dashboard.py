"""Dashboard — bekostiging van de eigen instelling in vijf tabs."""

import sys
from pathlib import Path

import altair as alt
import polars as pl
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
import _huisstijl as hs
from _chart_docs import chart_help
from _utils import datamodel_dir, lees_star

from ho_bekostiging_bestanden import indicatoren as ind
from ho_bekostiging_bestanden.stack import LABEL_COL

LEVERING_LABELS = {
    ind.DEFINITIEF: "Definitief (DEFBEK)",
    ind.VOORLOPIG: "Voorlopig (VLPBEK)",
}
# Npuls-blauw: eerste kleur van het Npuls-grafiekpalet (design tokens).
BALK_KLEUR = hs.grafiekpalet()[0]
HISTORIE_REEKSEN = 2  # deelname en resultaat
BALK_RONDING = 4  # px, afgeronde data-uiteinden
BALK_HOOGTE = 28  # pixels per balk
GETAL_FORMAAT = ",d"
LABEL_BREEDTE = 360  # max. pixels voor een as-label voordat het wordt afgekapt


# cache_resource: de tabellen worden alleen gelezen, niet gekopieerd per rerun;
# max_entries=1 omdat er steeds maar één actueel star schema is.
@st.cache_resource(show_spinner=False, max_entries=1)
def _star(pad: str, mtime: float) -> dict[str, pl.DataFrame] | None:
    return lees_star(Path(pad))


def _mtime(pad: Path) -> float:
    return max((p.stat().st_mtime for p in pad.glob("*.parquet")), default=0.0)


def _hbar(
    df: pl.DataFrame, label: str, waarde: str, formaat: str = GETAL_FORMAAT
) -> None:
    """Horizontale balken in de volgorde van ``df``."""
    grafiek = hs.opmaak(
        alt.Chart(
            df,
            mark=alt.MarkDef(
                type="bar", color=BALK_KLEUR, cornerRadiusEnd=BALK_RONDING
            ),
        )
        .encode(
            x=alt.X(
                waarde,
                title=None,
                # Aantallen: geen halve ticks (1, 1, 2, 2); aandelen: vrije ticks.
                axis=alt.Axis(
                    format=formaat,
                    tickMinStep=1 if formaat == GETAL_FORMAAT else alt.Undefined,
                ),
            ),
            y=alt.Y(
                label, title=None, sort=None, axis=alt.Axis(labelLimit=LABEL_BREEDTE)
            ),
            tooltip=[label, alt.Tooltip(waarde, format=formaat)],
        )
        .properties(height=alt.Step(BALK_HOOGTE))
    )
    st.altair_chart(grafiek, width="stretch")


def _tab_trechter(deelnames: pl.DataFrame, resultaten: pl.DataFrame) -> None:
    chart_help("trechter")
    for titel, df in (("Deelnames", deelnames), ("Graden", resultaten)):
        st.markdown(f"**{titel}**")
        _hbar(ind.trechter(df), "Stap", "Aantal")


def _tab_redenen(deelnames: pl.DataFrame, star: dict[str, pl.DataFrame]) -> None:
    chart_help("redenen")
    if deelnames.is_empty():
        st.info("Geen deelnames in deze selectie.")
        return
    redenen = ind.redenen_niet_bekostigd(deelnames, star)
    if redenen.is_empty():
        st.info("Alle beoordeelde deelnames in deze selectie zijn bekostigd.")
        return
    _hbar(redenen, "Omschrijving", "Aantal")
    st.dataframe(redenen, hide_index=True, width="stretch")


def _tab_opleiding(deelnames: pl.DataFrame) -> None:
    chart_help("per_opleiding")
    per_opl = ind.per_opleiding(deelnames)
    if per_opl.is_empty():
        st.info("Geen beoordeelde deelnames in deze selectie.")
        return
    per_opl = per_opl.with_columns(
        ind.label("{} ({})", "Opleidingscode", "Opleidingsniveau").alias("Opleiding")
    ).sort("AandeelBekostigd")
    _hbar(per_opl, "Opleiding", "AandeelBekostigd", formaat=".0%")
    st.dataframe(per_opl.drop("Opleiding"), hide_index=True, width="stretch")


def _tab_voorlopig_definitief(star: dict[str, pl.DataFrame]) -> None:
    chart_help("voorlopig_definitief")
    if not ind.vergelijkbare_jaren(star):
        st.info(
            "Verwerk een VLPBEK- én een DEFBEK-bestand van hetzelfde jaar "
            "om te vergelijken."
        )
        return
    verschil = ind.voorlopig_vs_definitief(star)
    if verschil.is_empty():
        st.info("Geen statuswijzigingen tussen voorlopig en definitief.")
        return
    verschil = verschil.with_columns(
        ind.label("{}: {} → {}", "Bekostigingsjaar", "Voorlopig", "Definitief").alias(
            "Wijziging"
        )
    )
    _hbar(verschil, "Wijziging", "Aantal")
    st.dataframe(verschil.drop("Wijziging"), hide_index=True, width="stretch")


def _tab_historie(star: dict[str, pl.DataFrame]) -> None:
    chart_help("historie")
    if not ind.heeft_soort(star, ind.HISTORISCH):
        st.info(
            "Verwerk een HISBEK-bestand om de bekostiging over meerdere jaren te zien."
        )
        return
    hist = ind.historie(star).with_columns(
        (pl.col("Bekostigd") / pl.col("Totaal")).alias("AandeelBekostigd")
    )
    grafiek = hs.opmaak(
        alt.Chart(hist, mark=alt.MarkDef(type="line", point=True)).encode(
            x=alt.X(
                "Bekostigingsjaar:O",
                title="Bekostigingsjaar",
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "AandeelBekostigd:Q",
                title="Aandeel bekostigd",
                axis=alt.Axis(format=".0%"),
            ),
            # Kleur én streepjes: reeksen niet alleen op kleur te onderscheiden.
            color=alt.Color(
                "Bron:N",
                title=None,
                scale=alt.Scale(range=hs.grafiekpalet()[:HISTORIE_REEKSEN]),
            ),
            strokeDash=alt.StrokeDash("Bron:N", title=None),
            tooltip=[
                "Bekostigingsjaar",
                "Bron",
                "Totaal",
                "Bekostigd",
                alt.Tooltip("AandeelBekostigd", format=".0%"),
            ],
        )
    )
    st.altair_chart(grafiek, width="stretch")
    st.dataframe(hist, hide_index=True, width="stretch")


st.title("Dashboard")

datamodel = datamodel_dir()
star = _star(str(datamodel), _mtime(datamodel))
if star is None:
    st.warning("Nog geen star schema — verwerk eerst de bestanden op de Home-pagina.")
    st.stop()

soorten = [s for s in LEVERING_LABELS if ind.heeft_soort(star, s)]
deelnames = ind.feiten(star, "fact_deelname", [])
resultaten = ind.feiten(star, "fact_resultaat", [])
if soorten:
    soort = st.sidebar.radio("Levering", soorten, format_func=LEVERING_LABELS.get)
    leveringen = ind.actuele_leveringen(star, soort)
    jaar_per_levering = dict(
        star["dim_levering"]
        .filter(pl.col(LABEL_COL).is_in(leveringen))
        .select("Bekostigingsjaar", LABEL_COL)
        .rows()
    )
    jaar = st.sidebar.selectbox(
        "Bekostigingsjaar", sorted(jaar_per_levering, reverse=True)
    )
    niveaus = st.sidebar.multiselect(
        "Opleidingsniveau",
        sorted(star["dim_opleiding"]["Opleidingsniveau"].drop_nulls().unique()),
        placeholder="Alle niveaus",
    )
    gekozen = [jaar_per_levering[jaar]]
    deelnames = ind.feiten(star, "fact_deelname", gekozen, niveaus)
    resultaten = ind.feiten(star, "fact_resultaat", gekozen, niveaus)
else:
    st.info("Er is alleen historische data (HISBEK); zie het tabblad Historie.")

tabs = st.tabs(
    [
        "Trechter",
        "Waarom niet bekostigd",
        "Per opleiding",
        "Voorlopig vs definitief",
        "Historie",
    ]
)
with tabs[0]:
    _tab_trechter(deelnames, resultaten)
with tabs[1]:
    _tab_redenen(deelnames, star)
with tabs[2]:
    _tab_opleiding(deelnames)
with tabs[3]:
    _tab_voorlopig_definitief(star)
with tabs[4]:
    _tab_historie(star)
