"""Home — ontdek de bestanden en verwerk ze in één stap."""

import sys
from pathlib import Path

import polars as pl
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from _huisstijl import hero
from _utils import output_dir, prepared_dir, pseudonimiseringssleutel, raw_dir

from ho_bekostiging_bestanden.ingest import parse_bestandsnaam
from ho_bekostiging_bestanden.kwaliteit import (
    ERNST_ERROR,
    ERNST_KOLOM,
    ERNST_WARNING,
    STATUS_FAIL,
)
from ho_bekostiging_bestanden.pipeline import (
    detect_levering,
    onherkende_bestanden,
    verwerk_alles,
    vind_bestanden,
)

UPLOAD_MAP = "upload"
GEEN_PSEUDONIMISERING_MELDING = (
    "Pseudonimisering staat uit: BSN en onderwijsnummer blijven leesbaar in de "
    "output. Koppelen met gepseudonimiseerde 1CHO-data kan dan niet; deel de "
    "output niet buiten de eigen instelling."
)
DEMO_SLEUTEL_MELDING = (
    "Demo-sleutel actief (uit `app/config.toml`): alleen geschikt voor de "
    "synthetische demo-data. Voor echte data en koppeling met 1CHO zet je "
    "`EENCIJFERHO_ENCRYPT_KEY` op dezelfde sleutel als in 1cijferho."
)


def _overzicht(bestanden: list[Path]) -> pl.DataFrame:
    rijen = []
    for pad in bestanden:
        info = parse_bestandsnaam(pad)
        if info is None:
            continue
        rijen.append(
            {
                "Bestand": info.bestandsnaam,
                "Soort": info.soort,
                "Bekostigingsjaar": info.bekostigingsjaar,
                "Aangemaakt": info.datum_aanmaak.isoformat(),
                "BRIN": info.brin,
            }
        )
    return pl.DataFrame(rijen)


def _bewaar_uploads(raw: Path) -> None:
    uploads = st.file_uploader(
        "Of voeg een los bestand toe (VLPBEK, DEFBEK of HISBEK)",
        type=["csv"],
        accept_multiple_files=True,
        key="upload",
    )
    for upload in uploads or []:
        if detect_levering(upload.name) is None:
            st.error(
                f"`{upload.name}` wordt niet herkend. Verwacht een naam als "
                "`VLPBEK_2025_20240115_99XX.csv`."
            )
            continue
        doel = raw / UPLOAD_MAP / upload.name
        doel.parent.mkdir(parents=True, exist_ok=True)
        doel.write_bytes(upload.getvalue())
        st.toast(f"{upload.name} toegevoegd")


hero(
    "HO-bekostigingsbestanden",
    "Zet DUO-analysebestanden (VLPBEK, DEFBEK, HISBEK) om naar een star schema.",
)

raw = raw_dir()
_bewaar_uploads(raw)
bestanden = vind_bestanden(raw)

onherkend = onherkende_bestanden(raw)
if onherkend:
    namen = "\n".join(f"- `{p.relative_to(raw)}`" for p in onherkend)
    st.warning(
        f"{len(onherkend)} CSV-bestand(en) niet herkend en overgeslagen. Verwacht "
        "een naam als `VLPBEK_2025_20240115_99XX.csv` (ook DEFBEK of HISBEK):"
        f"\n{namen}"
    )

if not bestanden:
    st.info(
        f"Geen herkenbare bestanden gevonden in `{raw}`. Zet VLPBEK-, DEFBEK- of "
        "HISBEK-bestanden in de invoermap of voeg ze hierboven toe."
    )
    st.stop()

st.subheader(f"{len(bestanden)} bestand(en) gevonden")
st.dataframe(_overzicht(bestanden), hide_index=True, width="stretch")

pseudonimiseer = st.checkbox(
    "Pseudonimiseer BSN en onderwijsnummer (aanbevolen; nodig voor koppeling met 1CHO)",
    value=True,
    key="pseudonimiseer",
)
sleutelstatus = pseudonimiseringssleutel()
if not pseudonimiseer:
    st.warning(GEEN_PSEUDONIMISERING_MELDING)
elif sleutelstatus.fout:
    st.error(f"Verwerken kan nog niet: {sleutelstatus.fout}")
elif sleutelstatus.is_demo:
    st.warning(DEMO_SLEUTEL_MELDING)

if st.button(
    "Verwerk alles",
    type="primary",
    key="verwerk_alles",
    disabled=pseudonimiseer and sleutelstatus.sleutel is None,
):
    with st.spinner("Bezig met verwerken…"):
        resultaat = verwerk_alles(
            raw,
            prepared_dir(),
            output_dir(),
            sleutel=sleutelstatus.sleutel if pseudonimiseer else None,
            pseudonimiseer=pseudonimiseer,
        )
    for naam, fout in resultaat.fouten.items():
        st.error(f"**{naam}** kon niet worden verwerkt: {fout}")
    meldingen = resultaat.meldingen
    fouten = meldingen.filter(pl.col(ERNST_KOLOM) == ERNST_ERROR)
    waarschuwingen = meldingen.filter(pl.col(ERNST_KOLOM) == ERNST_WARNING)
    if resultaat.status == STATUS_FAIL:
        st.error(
            f"Kwaliteitsstatus fail: {fouten.height} error(s). Het star schema is "
            "geschreven, maar de cijfers zijn niet betrouwbaar. Los de errors "
            "hieronder op en verwerk opnieuw."
        )
        st.dataframe(fouten.drop(ERNST_KOLOM), hide_index=True, width="stretch")
    if not waarschuwingen.is_empty():
        with st.expander(f"⚠️ {waarschuwingen.height} waarschuwing(en)"):
            st.dataframe(
                waarschuwingen.drop(ERNST_KOLOM), hide_index=True, width="stretch"
            )
    if resultaat.status != STATUS_FAIL:
        totaal = sum(df.height for df in resultaat.star.values())
        st.success(
            f"{len(resultaat.prepared_dirs)} bestand(en) verwerkt; star schema met "
            f"{len(resultaat.star)} tabellen en {totaal:,} rijen."
        )

col_dash, col_res = st.columns(2)
with col_dash:
    if st.button("Naar het dashboard →", width="stretch"):
        st.switch_page("pages/dashboard.py")
with col_res:
    if st.button("Naar de resultaten →", width="stretch"):
        st.switch_page("pages/resultaten.py")
