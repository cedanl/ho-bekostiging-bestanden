"""HISBEK-schema en codelijsten tegen de PvE, onafhankelijk van de TOML.

De lijsten hieronder zijn met de hand overgenomen uit de PvE HO-instelling –
DUO v26.3.1 (17-07-2026), bijlage 10, §19.7.2 (HRD) en §19.7.3 (HRR). Ze staan
bewust niet in het schema: demo en testdata worden met het schema gebouwd, dus
een fout in het schema zou anders ook in de tests zitten.
"""

import polars as pl
import pytest

from ho_bekostiging_bestanden.decode import decode_frames
from ho_bekostiging_bestanden.ingest import parse_bestandsnaam, read_multi_record_csv
from ho_bekostiging_bestanden.metadata import load_schema
from ho_bekostiging_bestanden.validate import valideer

from .conftest import analyse_regels, hisbek_regels, schrijf_bestand

PVE_VELDEN = {
    "HRD": [
        "Recordsoort", "Burgerservicenummer", "Onderwijsnummer", "Bekostigingsjaar",
        "BRIN", "Inschrijvingvolgnummer", "Bekostigingsindicatie",
        "CodeBekostigingstatus", "Bekostigingsniveau", "Opleidingscode",
        "Opleidingsniveau", "Opleidingsfase", "DatumInschrijving",
        "DatumUitschrijving", "EersteInschrijving", "Inschrijvingsvorm",
        "Onderwijsvorm", "DatumEersteAanlevering", "Bekostigingsduur", "ECTS",
        "ECTSBekostigd", "OpleidingOnderdeel", "Bekostigingscode",
        "IndicatieSectorLG", "IndicatieBaMa", "IndicatieAcademischZiekenhuis",
        "DuitseDeelstaat", "IndicatieWoonplaatsVereiste",
        "IndicatieNationaliteitsvoorwaardeSF", "IndicatieGBARelatie",
    ],
    "HRR": [
        "Recordsoort", "Burgerservicenummer", "Onderwijsnummer", "Bekostigingsjaar",
        "BRIN", "Resultaatvolgnummer", "Bekostigingsindicatie",
        "CodeBekostigingstatus", "Bekostigingsniveau", "JointDegreeFactor",
        "Opleidingscode", "Opleidingsniveau", "Opleidingsfase", "EersteGraad",
        "DatumDiploma", "Onderwijsvorm", "DatumEersteAanlevering",
        "OpleidingOnderdeel", "Bekostigingscode", "IndicatieSectorLG",
        "IndicatieBaMa", "IndicatieAcademischZiekenhuis",
        "IndicatieGraadTeltVoorBekostigingsloopbaan", "DuitseDeelstaat",
        "IndicatieWoonplaatsVereiste", "IndicatieNationaliteitsvoorwaardeSF",
        "IndicatieGBARelatie",
    ],
}  # fmt: skip

# Kolom "Verplicht = ja" in de PvE.
PVE_VERPLICHT = {
    "HRD": {
        "Recordsoort", "Bekostigingsjaar", "BRIN", "Bekostigingsindicatie",
        "CodeBekostigingstatus", "Opleidingscode", "Opleidingsniveau",
        "Opleidingsfase", "DatumInschrijving", "DatumUitschrijving",
        "EersteInschrijving", "Inschrijvingsvorm", "Onderwijsvorm",
        "IndicatieNationaliteitsvoorwaardeSF",
    },
    "HRR": {
        "Recordsoort", "Bekostigingsjaar", "BRIN", "Bekostigingsindicatie",
        "CodeBekostigingstatus", "JointDegreeFactor", "Opleidingscode",
        "Opleidingsniveau", "Opleidingsfase", "EersteGraad", "Onderwijsvorm",
        "IndicatieGraadTeltVoorBekostigingsloopbaan",
        "IndicatieNationaliteitsvoorwaardeSF",
    },
}  # fmt: skip

HISBEK_NAAM = "HISBEK_2024_20250301_99XX.csv"
VLPBEK_NAAM = "VLPBEK_2025_20240115_99XX.csv"


@pytest.mark.parametrize("rs", PVE_VELDEN)
def test_veldvolgorde_volgens_pve(rs):
    assert load_schema("hisbek")[rs]["fields"] == PVE_VELDEN[rs]


@pytest.mark.parametrize("rs", PVE_VERPLICHT)
def test_verplichte_velden_volgens_pve(rs):
    assert set(load_schema("hisbek")[rs]["required_fields"]) == PVE_VERPLICHT[rs]


def _zet(regels: list[str], schema: str, rs: str, veld: str, waarde: str) -> list[str]:
    """Zet ``veld`` op ``waarde`` in alle regels van recordsoort ``rs``."""
    index = load_schema(schema)[rs]["fields"].index(veld)
    uit = []
    for regel in regels:
        velden = regel.split("|")
        if velden[0] == rs:
            velden[index] = waarde
        uit.append("|".join(velden))
    return uit


def _codelijstmeldingen(tmp_path, naam: str, schema: str, regels: list[str]):
    pad = schrijf_bestand(tmp_path, naam, regels)
    info = parse_bestandsnaam(pad)
    assert info is not None
    frames = decode_frames(read_multi_record_csv(pad, schema), schema)
    rapport = valideer(frames, schema, info)
    return rapport.filter(pl.col("Melding").str.starts_with("Inschrijvingsvorm"))


@pytest.mark.parametrize("code", ["A", "T"])
def test_hisbek_kent_auditor_en_toegelaten_student(tmp_path, code):
    regels = _zet(hisbek_regels(), "hisbek", "HRD", "Inschrijvingsvorm", code)
    assert _codelijstmeldingen(tmp_path, HISBEK_NAAM, "hisbek", regels).is_empty()


def test_analysebestand_kent_geen_auditor(tmp_path):
    regels = _zet(analyse_regels(), "analyse", "BRD", "Inschrijvingsvorm", "A")
    assert not _codelijstmeldingen(tmp_path, VLPBEK_NAAM, "analyse", regels).is_empty()
