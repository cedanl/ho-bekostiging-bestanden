"""Npuls-huisstijl voor de app: kleuren, grafiekpalet en CSS uit de design tokens.

Bron: ``huisstijl/design-tokens.json``, letterlijk overgenomen uit de skill
``vormgever-npuls-huisstijl`` in ``cedanl/.github`` (zie ``huisstijl/README.md``).
Kleuren staan nergens anders hardcoded; het Streamlit-thema in
``.streamlit/config.toml`` wordt in de tests tegen deze tokens gecontroleerd.

Bewust géén bedrijfslogica.
"""

import json
from functools import cache
from pathlib import Path

import altair as alt
import streamlit as st

TOKENS_PAD = Path(__file__).parent / "huisstijl" / "design-tokens.json"
# Aantal reeksen uit `categorical_order` voor grafieken: blauw, oranje, groen.
# Geel valt af: te licht op wit volgens de dataviz-palletvalidator.
GRAFIEK_REEKSEN = 3
# `data_visualization.grid_and_axis`: grijs-200 voor gridlijnen, zwart voor astekst.
RASTER_KLEUR = "grijs-200"
ASTEKST_KLEUR = "npuls-zwart"
_KLEURGROEPEN = (("colors", "primary"), ("colors", "secondary"), ("neutrals",))


@cache
def tokens() -> dict:
    """De volledige Npuls design tokens."""
    with TOKENS_PAD.open(encoding="utf-8") as f:
        return json.load(f)


def kleur(naam: str) -> str:
    """Hex-waarde van een tokenkleur, bijv. ``"npuls-blauw"`` of ``"grijs-200"``.

    Raises:
        KeyError: Als de kleur niet in de tokens staat.
    """
    for pad in _KLEURGROEPEN:
        groep = tokens()
        for sleutel in pad:
            groep = groep[sleutel]
        if naam in groep:
            return groep[naam]
    raise KeyError(f"Onbekende Npuls-kleur: {naam}")


def feedback(soort: str) -> str:
    """Statuskleur: ``"succes"``, ``"info"``, ``"waarschuwing"`` of ``"fout"``."""
    return kleur(tokens()["feedback_colors"][soort])


def grafiekpalet() -> list[str]:
    """Categorische grafiekkleuren in de vaste Npuls-volgorde."""
    volgorde = tokens()["data_visualization"]["categorical_order"]
    return [kleur(naam) for naam in volgorde[:GRAFIEK_REEKSEN]]


def opmaak(grafiek: alt.Chart) -> alt.Chart:
    """Npuls-asopmaak: grijs-200 rasterlijnen, zwarte astekst."""
    raster, tekst = kleur(RASTER_KLEUR), kleur(ASTEKST_KLEUR)
    return grafiek.configure_axis(
        gridColor=raster, domainColor=raster, labelColor=tekst, titleColor=tekst
    )


def css() -> str:
    """Stylesheet: tokenvariabelen plus de componentklassen van de app."""
    variabelen = "\n".join(
        f"  {naam}: {waarde};"
        for naam, waarde in tokens()["css_variables"].items()
        if naam.startswith("--")
    )
    return f"""{tokens()["font_loading"]["google_fonts_import"]}
:root {{
{variabelen}
}}
h1, h2, h3 {{ font-family: var(--npuls-font-primary); font-weight: 600; }}
.npuls-hero {{
  position: relative;
  overflow: hidden;
  background: var(--npuls-blauw);
  border-radius: var(--npuls-radius-lg);
  padding: var(--npuls-space-2xl) var(--npuls-space-xl);
  margin-bottom: var(--npuls-space-lg);
}}
.npuls-hero h1 {{
  color: var(--npuls-geel);
  margin: 0 0 var(--npuls-space-sm) 0;
  font-size: 2.5rem;
}}
/* Tekst boven de ringen; de ondertitel blijft links van de ringen. */
.npuls-hero h1, .npuls-hero p {{ position: relative; }}
.npuls-hero p {{ max-width: 70%; }}
.npuls-hero p {{ color: var(--npuls-roze); margin: 0; font-size: 1.05rem; }}
.npuls-ringen {{
  position: absolute;
  right: -80px;
  bottom: -110px;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: repeating-radial-gradient(
    circle, transparent 0 20px, var(--npuls-roze) 20px 26px
  );
  opacity: 0.9;
}}
/* Rand om het rondje van een keuzeknop: tegen de licht-blauwe zijbalk is een
   lege keuzeknop anders onzichtbaar. LET OP: deze selector leunt op de interne
   DOM van Streamlit (1.64) en kan na een update stil ophouden met werken;
   controleer na een Streamlit-upgrade de zijbalk van het dashboard. */
[data-testid="stRadioOption"] > div > div:first-child {{
  box-shadow: inset 0 0 0 1.5px var(--npuls-blauw);
}}
"""


def pas_toe() -> None:
    """Laad de Npuls-stylesheet op de huidige pagina."""
    st.markdown(f"<style>{css()}</style>", unsafe_allow_html=True)


def hero(titel: str, ondertitel: str) -> None:
    """Kopblok in Npuls-blauw met gele titel en roze concentrische ringen."""
    st.markdown(
        f'<div class="npuls-hero"><div class="npuls-ringen"></div>'
        f"<h1>{titel}</h1><p>{ondertitel}</p></div>",
        unsafe_allow_html=True,
    )
