"""Documentatie per grafiek in het dashboard.

Elke grafiek in ``dashboard.py`` toont via :func:`chart_help` een uitklapbaar
uitlegblok: welke star-schema-variabelen gebruikt worden en, in gewone taal,
welke bewerking erachter zit. Waar iets nog bevestigd moet worden, staat dat
in de kanttekening.

Bewust géén bedrijfslogica; de berekeningen staan in ``indicatoren.py``.
"""

import streamlit as st

CHART_DOCS: dict[str, dict] = {
    "trechter": {
        "titel": "Bekostigingstrechter",
        "variabelen": [
            "fact_deelname / fact_resultaat",
            "CodeBekostigingstatus",
            "Bekostigingsindicatie",
            "dim_instelling.EigenInstelling",
        ],
        "manipulatie": (
            "Alleen rijen van de eigen instelling in de gekozen levering. "
            "**In bestand** = alle rijen. **Beoordeeld** = zonder status `mv` "
            "(inschrijving niet geldig op de peildatum; die rijen neemt DUO "
            "alleen mee voor het complete beeld). **Bekostigd** = beoordeeld én "
            "bekostigingsindicatie J."
        ),
        "kanttekening": (
            "Dat `mv` de juiste afbakening is voor 'beoordeeld' is een aanname "
            "op basis van PvE §17.5 en moet nog bevestigd worden."
        ),
    },
    "redenen": {
        "titel": "Waarom niet bekostigd?",
        "variabelen": [
            "fact_status.Code",
            "dim_status.Omschrijving",
            "dim_status.Groep",
            "Bekostigingsindicatie",
        ],
        "manipulatie": (
            "Van de beoordeelde, niet-bekostigde deelnames wordt elke statuscode "
            "apart geteld (een deelname met `na,ti` telt bij beide codes). Codes "
            "die 'bekostigd' betekenen, vallen weg."
        ),
        "kanttekening": (
            "De groepen (zoals 'Aanlevering' of 'Verbruik en limieten') zijn een "
            "eigen indeling, niet van DUO."
        ),
    },
    "per_opleiding": {
        "titel": "Aandeel bekostigd per opleiding",
        "variabelen": [
            "Opleidingscode",
            "dim_opleiding.Opleidingsniveau",
            "Bekostigingsindicatie",
        ],
        "manipulatie": (
            "Per opleidingscode: het aantal beoordeelde deelnames van de eigen "
            "instelling en het deel daarvan met bekostigingsindicatie J."
        ),
    },
    "voorlopig_definitief": {
        "titel": "Voorlopig tegenover definitief",
        "variabelen": [
            "dim_levering.SoortLevering",
            "Bekostigingsjaar",
            "BRIN",
            "Inschrijvingvolgnummer",
            "_persoon_id",
            "CodeBekostigingstatus",
        ],
        "manipulatie": (
            "Per bekostigingsjaar wordt de nieuwste VLPBEK naast de nieuwste "
            "DEFBEK gelegd. Deelnames worden gekoppeld op jaar, BRIN, "
            "inschrijvingvolgnummer en persoon; getoond worden alleen de "
            "deelnames waarvan de statuscode veranderde. Alleen jaren waarvoor "
            "zowel een VLPBEK als een DEFBEK is verwerkt, tellen mee."
        ),
    },
    "historie": {
        "titel": "Bekostiging per jaar (historisch)",
        "variabelen": [
            "dim_levering.SoortLevering = HISBEK",
            "Bekostigingsjaar",
            "Bekostigingsindicatie",
        ],
        "manipulatie": (
            "Uit het HISBEK-bestand: per bekostigingsjaar het aantal deelnames en "
            "graden van de eigen instelling en hoeveel daarvan bekostigd zijn."
        ),
        "kanttekening": "Alleen zichtbaar als er een HISBEK-bestand is verwerkt.",
    },
}


def chart_help(sleutel: str) -> None:
    """Toon een uitklapbaar uitlegblok voor een grafiek."""
    doc = CHART_DOCS[sleutel]
    with st.expander(f"ℹ️ Toelichting: {doc['titel']}"):
        st.markdown(doc["manipulatie"])
        st.caption("Variabelen: " + ", ".join(f"`{v}`" for v in doc["variabelen"]))
        if "kanttekening" in doc:
            st.warning(doc["kanttekening"])
