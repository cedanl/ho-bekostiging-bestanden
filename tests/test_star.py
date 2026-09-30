from datetime import date

import polars as pl
import pytest

from ho_bekostiging_bestanden.pipeline import run_pipeline
from ho_bekostiging_bestanden.pseudonimisering import laad_sleutel, pseudoniem
from ho_bekostiging_bestanden.stack import stack_prepared
from ho_bekostiging_bestanden.star import FEIT_ID, PERSOON_ID, STAR_TABELLEN, build_star

SLEUTELS = {
    "dim_levering": "levering",
    "dim_persoon": PERSOON_ID,
    "dim_instelling": "BRIN",
    "dim_opleiding": "Opleidingscode",
    "dim_status": "Code",
}
VERWIJZINGEN = [
    ("fact_deelname", "levering", "dim_levering"),
    ("fact_deelname", PERSOON_ID, "dim_persoon"),
    ("fact_deelname", "BRIN", "dim_instelling"),
    ("fact_deelname", "Opleidingscode", "dim_opleiding"),
    ("fact_resultaat", "levering", "dim_levering"),
    ("fact_resultaat", PERSOON_ID, "dim_persoon"),
    ("fact_resultaat", "BRIN", "dim_instelling"),
    ("fact_resultaat", "Opleidingscode", "dim_opleiding"),
    ("fact_status", "Code", "dim_status"),
    ("fact_loopbaan", PERSOON_ID, "dim_persoon"),
]


def _star(tmp_path, *bestanden):
    mappen = []
    for bestand in bestanden:
        doel = tmp_path / "prep" / bestand.stem
        run_pipeline(bestand, doel)
        mappen.append(doel)
    return build_star(stack_prepared(mappen))


@pytest.fixture
def star(tmp_path, vlpbek_bestand, hisbek_bestand):
    return _star(tmp_path, vlpbek_bestand, hisbek_bestand)


def test_alle_tabellen(star):
    assert tuple(star) == STAR_TABELLEN


@pytest.mark.parametrize("tabel,sleutel", SLEUTELS.items())
def test_dimensiesleutels_uniek(star, tabel, sleutel):
    kolom = star[tabel][sleutel]
    assert kolom.null_count() == 0
    assert kolom.n_unique() == star[tabel].height


@pytest.mark.parametrize("feit,sleutel,dim", VERWIJZINGEN)
def test_geen_verweesde_verwijzingen(star, feit, sleutel, dim):
    waarden = set(star[feit][sleutel].drop_nulls())
    assert waarden <= set(star[dim][SLEUTELS[dim]])


def test_brugtabel_verwijst_naar_feiten(star):
    feit_ids = set(star["fact_deelname"][FEIT_ID]) | set(
        star["fact_resultaat"][FEIT_ID]
    )
    assert set(star["fact_status"][FEIT_ID]) <= feit_ids


def test_fact_deelname_bevat_brd_en_hrd(star):
    feit = star["fact_deelname"]
    assert feit.height == 5
    assert feit["Recordsoort"].value_counts().sort("Recordsoort").rows() == [
        ("BRD", 3),
        ("HRD", 2),
    ]
    assert feit["Bekostigingsjaar"].null_count() == 0
    assert sorted(feit["Bekostigingsjaar"].unique()) == [2023, 2024, 2025]
    assert "Burgerservicenummer" not in feit.columns
    assert "Opleidingsniveau" not in feit.columns


def test_persoon_zonder_bsn_krijgt_onderwijsnummer(star):
    onr = pseudoniem(laad_sleutel(), "800010002")
    assert onr in star["dim_persoon"][PERSOON_ID].to_list()


def test_meervoudige_status_wordt_gesplitst(star):
    na_ti = star["fact_deelname"].filter(pl.col("CodeBekostigingstatus") == "na,ti")
    codes = star["fact_status"].filter(pl.col(FEIT_ID) == na_ti[FEIT_ID][0])["Code"]
    assert sorted(codes) == ["na", "ti"]


def test_eigen_instelling(star):
    dim = dict(star["dim_instelling"].select("BRIN", "EigenInstelling").rows())
    assert dim == {"99XX": True, "71AA": False}


def test_graaddatum_in_dim_persoon(star):
    bsn = pseudoniem(laad_sleutel(), "700010001")
    persoon = star["dim_persoon"].filter(pl.col(PERSOON_ID) == bsn)
    assert persoon["DatumGraadBehaaldBa"][0] == date(2023, 6, 25)


def test_dim_status_compleet(star):
    assert star["dim_status"].height == 34
    assert star["dim_status"].schema["Bekostigd"] == pl.Boolean


def test_alleen_hisbek(tmp_path, hisbek_bestand):
    star = _star(tmp_path, hisbek_bestand)
    assert tuple(star) == STAR_TABELLEN
    assert star["fact_loopbaan"].is_empty()
    assert {"levering", PERSOON_ID} <= set(star["fact_loopbaan"].columns)
    assert star["fact_resultaat"].height == 1


def test_lege_invoer_geeft_lege_tabellen():
    star = build_star({})
    assert tuple(star) == STAR_TABELLEN
    assert all(star[t].is_empty() for t in STAR_TABELLEN if t != "dim_status")
    assert "Bekostigingsjaar" in star["fact_deelname"].columns
