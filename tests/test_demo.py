import polars as pl

from ho_bekostiging_bestanden.demo import genereer_demo
from ho_bekostiging_bestanden.kwaliteit import STATUS_OK
from ho_bekostiging_bestanden.pipeline import verwerk_alles

from .conftest import DEMO_RAW

VERWACHT = {
    "VLPBEK_2025_20240115_99XX.csv",
    "VLPBEK_2026_20250115_99XX.csv",
    "DEFBEK_2025_20240715_99XX.csv",
    "HISBEK_2024_20250301_99XX.csv",
}


def test_generator_is_deterministisch(tmp_path):
    a = genereer_demo(tmp_path / "a")
    b = genereer_demo(tmp_path / "b")
    assert {p.name for p in a} == VERWACHT
    for pa, pb in zip(sorted(a), sorted(b), strict=True):
        assert pa.read_bytes() == pb.read_bytes()


def test_demo_in_git_is_actueel(tmp_path):
    for pad in genereer_demo(tmp_path):
        assert (DEMO_RAW / pad.name).read_bytes() == pad.read_bytes(), pad.name


def test_demo_verwerkt_zonder_fouten_of_meldingen(tmp_path):
    resultaat = verwerk_alles(DEMO_RAW, tmp_path / "prep", tmp_path / "out")
    assert resultaat.fouten == {}
    assert resultaat.status == STATUS_OK
    assert resultaat.meldingen.is_empty(), resultaat.meldingen.to_dicts()


def test_demo_is_gevarieerd(demo_star):
    assert demo_star["dim_levering"].height == 4
    assert demo_star["fact_status"]["Code"].n_unique() >= 10
    assert "71AA" in demo_star["dim_instelling"]["BRIN"].to_list()
    assert demo_star["dim_persoon"]["Burgerservicenummer"].null_count() > 0
    assert demo_star["fact_loopbaan"]["AantalBekostigdeInschrijvingenMa_NVT"].any()


def test_definitief_herstelt_te_laat_aangeleverd(demo_star):
    feit = (
        demo_star["fact_deelname"]
        .join(demo_star["dim_levering"], on="levering")
        .filter(pl.col("Bekostigingsjaar") == 2025)
    )
    ti = feit.filter(pl.col("CodeBekostigingstatus").str.contains("ti"))
    per_soort = dict(ti.group_by("SoortLevering").len().rows())
    assert per_soort["DEFBEK"] < per_soort["VLPBEK"]
