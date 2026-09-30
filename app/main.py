"""Streamlit-app entrypoint."""

import streamlit as st
from _huisstijl import pas_toe

st.set_page_config(
    page_title="HO-bekostigingsbestanden",
    page_icon="📊",
    layout="centered",
)

# Npuls-huisstijl op elke pagina (main.py draait vóór elke pagina).
pas_toe()

# st.navigation is in Streamlit zowel module als functie; ty ziet de module.
pg = st.navigation(  # ty: ignore[call-non-callable]
    [
        st.Page("pages/home.py", title="Home", default=True),
        st.Page("pages/dashboard.py", title="Dashboard"),
        st.Page("pages/resultaten.py", title="Resultaten"),
    ],
    position="sidebar",
)
pg.run()
