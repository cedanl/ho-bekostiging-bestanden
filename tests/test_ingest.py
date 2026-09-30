from datetime import date

import pytest

from ho_bekostiging_bestanden.ingest import (
    MELDINGEN,
    Bestandsinfo,
    parse_bestandsnaam,
    read_multi_record_csv,
)
from ho_bekostiging_bestanden.metadata import load_schema

from .conftest import analyse_regels, schrijf_bestand


def test_parse_bestandsnaam_vlpbek():
    info = parse_bestandsnaam("data/VLPBEK_2025_20240115_99XX.csv")
    assert info == Bestandsinfo(
        soort="VLPBEK",
        bekostigingsjaar=2025,
        datum_aanmaak=date(2024, 1, 15),
        brin="99XX",
        bestandsnaam="VLPBEK_2025_20240115_99XX.csv",
    )


@pytest.mark.parametrize(
    "naam",
    [
        "defbek_2025_20240715_99xx.CSV",  # kleine letters, hoofdletter-extensie
        "DEFBEK_ 2025_20240715_99XX.CSV",  # spatie zoals in de PvE-notatie
    ],
)
def test_parse_bestandsnaam_varianten(naam):
    info = parse_bestandsnaam(naam)
    assert info is not None
    assert (info.soort, info.brin) == ("DEFBEK", "99XX")


@pytest.mark.parametrize(
    "naam",
    [
        "RO_27DV_20240731_20260324.csv",
        "VLPBEK_2025_20240115_99XX.txt",
        "VLPBEK_2025_20241340_99XX.csv",  # ongeldige datum
        "XYZBEK_2025_20240115_99XX.csv",
    ],
)
def test_parse_bestandsnaam_onbekend(naam):
    assert parse_bestandsnaam(naam) is None


def test_read_splitst_per_recordsoort(vlpbek_bestand):
    frames = read_multi_record_csv(vlpbek_bestand, "analyse")
    schema = load_schema("analyse")
    hoogtes = {rs: frames[rs].height for rs in ["VLP", "BLB", "BRD", "BRR", "SLR"]}
    assert hoogtes == {"VLP": 1, "BLB": 1, "BRD": 3, "BRR": 1, "SLR": 1}
    for rs in hoogtes:
        assert frames[rs].columns == schema[rs]["fields"]


def test_crlf_en_opvulling_verdwijnen(vlpbek_bestand):
    frames = read_multi_record_csv(vlpbek_bestand, "analyse")
    assert frames["SLR"]["AantalBRRrecords"][0] == "1"
    assert frames["BRD"]["IndicatieGBARelatie"].to_list() == ["J", "J", "J"]
    assert frames[MELDINGEN].height == 0


def test_onbekende_recordsoort_wordt_gemeld(tmp_path):
    regels = analyse_regels()
    regels.insert(2, "XYZ|iets")
    pad = schrijf_bestand(tmp_path, "VLPBEK_2025_20240115_99XX.csv", regels)
    meldingen = read_multi_record_csv(pad, "analyse")[MELDINGEN]
    assert meldingen.height == 1
    assert meldingen.row(0, named=True) == {
        "Regelnummer": 3,
        "Recordsoort": "XYZ",
        "Melding": "Onbekende recordsoort",
    }


def test_extra_gevulde_velden_worden_gemeld(tmp_path):
    regels = analyse_regels()
    regels[0] = regels[0] + "|extra"
    pad = schrijf_bestand(tmp_path, "VLPBEK_2025_20240115_99XX.csv", regels)
    meldingen = read_multi_record_csv(pad, "analyse")[MELDINGEN]
    assert meldingen["Recordsoort"].to_list() == ["VLP"]
    assert "meer gevulde velden" in meldingen["Melding"][0]


def test_latin1_bestand_is_leesbaar(tmp_path):
    pad = tmp_path / "VLPBEK_2025_20240115_99XX.csv"
    tekst = "\r\n".join(analyse_regels()).replace("INS002", "INSé02")
    pad.write_bytes(tekst.encode("latin-1"))
    frames = read_multi_record_csv(pad, "analyse")
    assert "INSé02" in frames["BRD"]["Inschrijvingvolgnummer"].to_list()


def test_leeg_bestand_geeft_fout(tmp_path):
    pad = tmp_path / "VLPBEK_2025_20240115_99XX.csv"
    pad.write_text("\r\n\r\n")
    with pytest.raises(ValueError, match="Leeg bestand"):
        read_multi_record_csv(pad, "analyse")


def test_ontbrekend_bestand_geeft_fout(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_multi_record_csv(tmp_path / "bestaat_niet.csv", "analyse")
