from datetime import date

import polars as pl

from ho_bekostiging_bestanden.decode import decode_frames
from ho_bekostiging_bestanden.ingest import MELDINGEN, read_multi_record_csv

from .conftest import analyse_regels, maak_regel, schrijf_bestand


def _decode(tmp_path, regels, schema="analyse"):
    pad = schrijf_bestand(tmp_path, "VLPBEK_2025_20240115_99XX.csv", regels)
    return decode_frames(read_multi_record_csv(pad, schema), schema)


def test_datums_en_booleans(vlpbek_bestand):
    frames = decode_frames(read_multi_record_csv(vlpbek_bestand, "analyse"), "analyse")
    brd = frames["BRD"]
    assert brd.schema["DatumInschrijving"] == pl.Date
    assert brd["DatumInschrijving"][0] == date(2023, 9, 1)
    assert brd.schema["Bekostigingsindicatie"] == pl.Boolean
    assert brd["Bekostigingsindicatie"].to_list() == [True, False, False]
    assert frames["VLP"]["Bekostigingsjaar"][0] == 2025
    assert frames["BRR"]["JointDegreeFactor"][0] == 1.0


def test_lege_tekst_wordt_null(vlpbek_bestand):
    frames = decode_frames(read_multi_record_csv(vlpbek_bestand, "analyse"), "analyse")
    assert frames["BRD"]["Burgerservicenummer"].to_list()[-1] is None
    assert "_Ruw" not in "".join(frames["BRD"].columns)


def test_ongeldige_datum_bewaart_ruwe_waarde(tmp_path):
    regels = analyse_regels()
    regels[1] = maak_regel(
        "analyse",
        "BLB",
        Burgerservicenummer="700010001",
        DatumGraadBehaaldBa="20230000",
    )
    blb = _decode(tmp_path, regels)["BLB"]
    assert blb["DatumGraadBehaaldBa"][0] is None
    assert blb["DatumGraadBehaaldBa_Ruw"][0] == "20230000"


def test_min_een_wordt_nvt(vlpbek_bestand):
    blb = decode_frames(read_multi_record_csv(vlpbek_bestand, "analyse"), "analyse")[
        "BLB"
    ]
    assert blb["AantalBekostigdeInschrijvingenMa"][0] is None
    assert blb["AantalBekostigdeInschrijvingenMa_NVT"][0] is True
    assert blb["AantalBekostigdeInschrijvingenBa"][0] == 1
    assert blb["AantalBekostigdeInschrijvingenBa_NVT"][0] is False


def test_statuscode_wordt_genormaliseerd(tmp_path):
    brd = _decode(tmp_path, analyse_regels(statussen=("pi", "mv", " TI, na")))["BRD"]
    assert brd["CodeBekostigingstatus"].to_list() == ["pi", "mv", "na,ti"]


def test_hisbek_float_met_komma(tmp_path):
    from .conftest import hisbek_regels

    regels = [r.replace("60.0", "60,5") for r in hisbek_regels()]
    hrd = _decode(tmp_path, regels, schema="hisbek")["HRD"]
    assert hrd["ECTS"].to_list() == [60.5, 60.5]
    assert hrd.schema["Bekostigingsjaar"] == pl.Int64


def test_meldingen_blijven_ongewijzigd(tmp_path):
    regels = analyse_regels()
    regels.insert(1, "XYZ|x")
    frames = _decode(tmp_path, regels)
    assert frames[MELDINGEN].height == 1
