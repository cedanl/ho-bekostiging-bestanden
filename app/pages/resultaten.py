"""Resultaten — blader door de star-schema-tabellen en download ze."""

import sys
from pathlib import Path

import polars as pl
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from _tabel_docs import PAGINA_INTRO, tabel_help
from _utils import datamodel_dir

from ho_bekostiging_bestanden.star import STAR_TABELLEN

# Eén versie per tabel in het geheugen; oude versies (vorige verwerking) vallen weg.
CACHE_TABELLEN = len(STAR_TABELLEN)

VOORBEELD_RIJEN = 1_000


@st.cache_resource(show_spinner=False, max_entries=CACHE_TABELLEN)
def _lees_tabel(pad: str, mtime: float) -> pl.DataFrame:
    """Houdt een gelezen Parquet-tabel in het geheugen tussen reruns."""
    return pl.read_parquet(pad)


@st.cache_data(show_spinner=False, max_entries=CACHE_TABELLEN)
def _tabel_csv(pad: str, mtime: float) -> str:
    """Maakt de CSV-tekst één keer per bestand in plaats van bij elke rerun."""
    return _lees_tabel(pad, mtime).write_csv()


st.title("Resultaten")
st.info(PAGINA_INTRO)

datamodel = datamodel_dir()
tabellen = {
    naam: datamodel / f"{naam}.parquet"
    for naam in STAR_TABELLEN
    if (datamodel / f"{naam}.parquet").exists()
}

if not tabellen:
    st.warning("Geen resultaten — verwerk eerst de bestanden op de Home-pagina.")
    if st.button("← Home"):
        st.switch_page("pages/home.py")
    st.stop()

gekozen = st.selectbox("Kies tabel", list(tabellen), key="resultaten_tabel")
if gekozen:
    pad = tabellen[gekozen]
    tabel_help(gekozen)
    mtime = pad.stat().st_mtime
    df = _lees_tabel(str(pad), mtime)

    col_rijen, col_kolommen = st.columns(2)
    col_rijen.metric("Rijen", f"{df.height:,}")
    col_kolommen.metric("Kolommen", f"{df.width:,}")

    st.dataframe(df.head(VOORBEELD_RIJEN), width="stretch", hide_index=True)
    if df.height > VOORBEELD_RIJEN:
        st.caption(f"Eerste {VOORBEELD_RIJEN:,} van {df.height:,} rijen getoond.")

    st.download_button(
        label=f"Download `{gekozen}.csv`",
        data=_tabel_csv(str(pad), mtime),
        file_name=f"{gekozen}.csv",
        mime="text/csv",
        width="stretch",
    )
