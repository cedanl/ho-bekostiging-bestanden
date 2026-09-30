"""Documentatie per tabel op de Resultaten-pagina.

Elke star-schema-tabel krijgt via :func:`tabel_help` een uitklapbaar
uitlegblok in gewone taal: wát de tabel bevat en uit welk DUO-bestand
(VLPBEK/DEFBEK/HISBEK) de gegevens komen.

Bewust géén bedrijfslogica; het model leeft in ``src/.../star.py``.
"""

import streamlit as st

PAGINA_INTRO = (
    "Op deze pagina blader je door de verwerkte tabellen (het **star schema**). "
    "Kies een tabel, bekijk de eerste 1 000 rijen en download desgewenst de "
    "volledige tabel als CSV.\n\n"
    "Een tabel kan **leeg** zijn als het bijbehorende bestand niet is verwerkt "
    "(bijvoorbeeld geen HISBEK-bestand). Dat is geen fout."
)

TABEL_DOCS: dict[str, dict[str, str]] = {
    "dim_levering": {
        "titel": "Leveringen",
        "wat": (
            "Eén regel per verwerkt bestand: soort levering (VLPBEK = voorlopig, "
            "DEFBEK = definitief, HISBEK = historisch), bekostigingsjaar, "
            "aanmaakdatum, de instelling (BRIN) die het bestand ontving en of "
            "BSN en onderwijsnummer gepseudonimiseerd zijn."
        ),
        "bron": "Bestandsnaam en voorlooprecord (VLP) van elk bestand.",
    },
    "dim_persoon": {
        "titel": "Personen",
        "wat": (
            "Eén regel per student, met (standaard gepseudonimiseerd) BSN en/of "
            "onderwijsnummer en de datums waarop een eerste AD-, bachelor- of "
            "mastergraad is behaald. De pseudoniemen zijn gelijk aan die van "
            "1cijferho (met dezelfde sleutel), zodat je op `Burgerservicenummer` "
            "met 1CHO kunt koppelen. `_persoon_id` is het BSN-pseudoniem, of dat "
            "van het onderwijsnummer als er geen BSN is."
        ),
        "bron": "BLB-records (loopbaan) en de persoonsnummers in BRD/BRR/HRD/HRR.",
    },
    "dim_instelling": {
        "titel": "Instellingen",
        "wat": (
            "Alle instellingen (BRIN) waar de studenten ingeschreven stonden of "
            "een graad behaalden. `EigenInstelling` geeft aan welke BRIN de "
            "bestanden heeft ontvangen; de andere zijn instellingen waar dezelfde "
            "studenten óók stonden ingeschreven."
        ),
        "bron": "BRD/BRR/HRD/HRR en het voorlooprecord.",
    },
    "dim_opleiding": {
        "titel": "Opleidingen",
        "wat": (
            "Eén regel per opleidingscode (ISAT/CROHO) met opleidingsniveau "
            "(bijv. HBO-BA), onderdeel (bijv. TECHNIEK) en de indicaties voor de "
            "LG-sector en het academisch ziekenhuis. Opleidingsnamen zitten niet "
            "in de DUO-bestanden."
        ),
        "bron": "BRD/BRR/HRD/HRR; bij verschillen telt de nieuwste levering.",
    },
    "dim_status": {
        "titel": "Bekostigingsstatussen",
        "wat": (
            "De 34 statuscodes uit de PvE met omschrijving, een groep en of de "
            "code 'bekostigd' betekent. De groepen zijn een eigen indeling, "
            "niet van DUO."
        ),
        "bron": "PvE HO-instelling – DUO, §19.7.5.",
    },
    "fact_deelname": {
        "titel": "Deelnames (inschrijvingen)",
        "wat": (
            "Eén regel per inschrijving per levering, met bekostigingsindicatie "
            "(J/N), statuscode(s), opleidingsfase, onderwijsvorm en datums. Bevat "
            "ook inschrijvingen bij andere instellingen van dezelfde studenten."
        ),
        "bron": "BRD-records (VLPBEK/DEFBEK) en HRD-records (HISBEK).",
    },
    "fact_resultaat": {
        "titel": "Resultaten (graden)",
        "wat": (
            "Eén regel per behaalde graad per levering, met bekostigingsindicatie, "
            "statuscode, datum diploma en joint-degree-factor."
        ),
        "bron": "BRR-records (VLPBEK/DEFBEK) en HRR-records (HISBEK).",
    },
    "fact_status": {
        "titel": "Statuscodes per deelname of resultaat",
        "wat": (
            "Koppeltabel: een deelname met status `na,ti` staat hier twee keer, "
            "één keer per code. Zo kun je per reden tellen."
        ),
        "bron": "Veld CodeBekostigingstatus uit de deelnames en resultaten.",
    },
    "fact_loopbaan": {
        "titel": "Bekostigingsloopbaan",
        "wat": (
            "Per student en levering: het aantal al bekostigde inschrijfjaren "
            "(verbruik) per type opleiding. Leeg (n.v.t.) als er door een eerder "
            "behaalde graad niets meer bekostigd kan worden."
        ),
        "bron": "BLB-records; alleen in VLPBEK/DEFBEK, dus leeg met alleen HISBEK.",
    },
}


def tabel_help(naam: str) -> None:
    """Toon een uitklapbaar uitlegblok voor een star-tabel."""
    doc = TABEL_DOCS.get(naam)
    if doc is None:
        return
    with st.expander(f"ℹ️ Wat staat er in *{doc['titel']}*?"):
        st.markdown(doc["wat"])
        st.caption(f"Bron: {doc['bron']}")
