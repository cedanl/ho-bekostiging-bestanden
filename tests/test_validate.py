import pytest

from ho_bekostiging_bestanden.decode import decode_frames
from ho_bekostiging_bestanden.ingest import parse_bestandsnaam, read_multi_record_csv
from ho_bekostiging_bestanden.kwaliteit import (
    ERNST_ERROR,
    ERNST_WARNING,
    MELDING_SCHEMA,
)
from ho_bekostiging_bestanden.validate import valideer

from .conftest import analyse_regels, maak_regel, schrijf_bestand

NAAM = "VLPBEK_2025_20240115_99XX.csv"


def _info(pad):
    info = parse_bestandsnaam(pad)
    assert info is not None
    return info


def _valideer(tmp_path, regels, naam=NAAM):
    pad = schrijf_bestand(tmp_path, naam, regels)
    frames = decode_frames(read_multi_record_csv(pad, "analyse"), "analyse")
    return valideer(frames, "analyse", _info(pad))


def test_schoon_bestand_geeft_geen_meldingen(tmp_path):
    rapport = _valideer(tmp_path, analyse_regels())
    assert rapport.schema == MELDING_SCHEMA
    assert rapport.height == 0


def test_hisbek_schoon(hisbek_bestand):
    frames = decode_frames(read_multi_record_csv(hisbek_bestand, "hisbek"), "hisbek")
    rapport = valideer(frames, "hisbek", _info(hisbek_bestand))
    assert rapport.height == 0


def test_slr_telling_klopt_niet(tmp_path):
    regels = analyse_regels()
    regels[-1] = maak_regel(
        "analyse",
        "SLR",
        AantalBLBrecords="1",
        AantalBRDrecords="4",
        AantalBRRrecords="1",
    )
    rapport = _valideer(tmp_path, regels)
    rij = rapport.row(0, named=True)
    assert (rij["Controle"], rij["Recordsoort"]) == ("Aantal records", "BRD")
    assert rij["Melding"] == "SLR meldt 4, gevonden 3"


def test_verplicht_veld_leeg(tmp_path):
    regels = analyse_regels()
    regels[2] = regels[2].replace("|34001|", "||", 1)
    rapport = _valideer(tmp_path, regels)
    rij = rapport.filter(rapport["Controle"] == "Verplicht veld").row(0, named=True)
    assert rij["Melding"] == "Opleidingscode is leeg"
    assert rij["Aantal"] == 1


def test_onbekende_code(tmp_path):
    rapport = _valideer(tmp_path, analyse_regels(statussen=("pi", "zz", "na,qq")))
    codes = rapport.filter(rapport["Controle"] == "Codelijst")["Melding"].to_list()
    assert sorted(codes) == [
        "CodeBekostigingstatus: onbekende code 'qq'",
        "CodeBekostigingstatus: onbekende code 'zz'",
    ]


def test_brin_in_naam_wijkt_af_is_error(tmp_path):
    rapport = _valideer(
        tmp_path, analyse_regels(), naam="VLPBEK_2025_20240115_00AA.csv"
    )
    assert rapport["Controle"].to_list() == ["BRIN"]
    assert rapport["Ernst"].to_list() == [ERNST_ERROR]
    assert "00AA" in rapport["Melding"][0]


def test_jaar_in_naam_wijkt_af_is_warning(tmp_path):
    rapport = _valideer(
        tmp_path, analyse_regels(), naam="VLPBEK_2024_20240115_99XX.csv"
    )
    assert rapport["Controle"].to_list() == ["Bekostigingsjaar"]
    assert rapport["Ernst"].to_list() == [ERNST_WARNING]


def test_onbekende_code_is_warning(tmp_path):
    rapport = _valideer(tmp_path, analyse_regels(statussen=("pi", "zz", "mv")))
    assert rapport["Ernst"].to_list() == [ERNST_WARNING]


@pytest.mark.parametrize(
    "wijziging",
    ["onbekende_recordsoort", "extra_veld", "slr", "verplicht"],
)
def test_structurele_afwijking_is_error(tmp_path, wijziging):
    regels = analyse_regels()
    if wijziging == "onbekende_recordsoort":
        regels.insert(1, "XYZ|x")
    elif wijziging == "extra_veld":
        regels[2] = regels[2] + "|" * 30 + "EXTRA"
    elif wijziging == "slr":
        regels[-1] = regels[-1].replace("|3|", "|4|", 1)
    else:
        regels[2] = regels[2].replace("|34001|", "||", 1)
    rapport = _valideer(tmp_path, regels)
    assert ERNST_ERROR in rapport["Ernst"].to_list(), rapport.to_dicts()


def test_meldingen_uit_ingest_komen_mee(tmp_path):
    regels = analyse_regels()
    regels.insert(1, "XYZ|x")
    regels.insert(2, "XYZ|y")
    rapport = _valideer(tmp_path, regels)
    rij = rapport.row(0, named=True)
    assert (rij["Controle"], rij["Recordsoort"], rij["Aantal"]) == ("Inlezen", "XYZ", 2)


def test_zonder_vlp_is_fout(tmp_path):
    with pytest.raises(ValueError, match="VLP"):
        _valideer(tmp_path, analyse_regels()[1:])
