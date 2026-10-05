import polars as pl
import pytest

from ho_bekostiging_bestanden.demo import genereer_demo
from ho_bekostiging_bestanden.ingest import read_multi_record_csv
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


@pytest.fixture(scope="module")
def demo_hisbek(tmp_path_factory) -> dict[str, pl.DataFrame]:
    """De vers gegenereerde HISBEK, ingelezen als tekst per recordsoort."""
    paden = genereer_demo(tmp_path_factory.mktemp("demo_hisbek"))
    (pad,) = [p for p in paden if p.name.startswith("HISBEK")]
    return read_multi_record_csv(pad, "hisbek")


@pytest.mark.parametrize("rs", ["HRD", "HRR"])
def test_hisbek_records_per_persoon_aflopend_op_jaar(demo_hisbek, rs):
    # PvE §19.5: per persoon aflopend op bekostigingsjaar.
    jaren = demo_hisbek[rs].select(
        "Onderwijsnummer", pl.col("Bekostigingsjaar").cast(pl.Int64)
    )
    oplopend = jaren.filter(
        pl.col("Bekostigingsjaar").diff().over("Onderwijsnummer") > 0
    )
    assert oplopend.is_empty()


def test_hisbek_ects_alleen_bij_open_universiteit(demo_hisbek):
    # PvE §19.7.2: alleen gevuld voor OU-deelnames; de demo-instelling is geen OU.
    hrd = demo_hisbek["HRD"]
    assert (hrd["ECTS"] == "").all()
    assert (hrd["ECTSBekostigd"] == "").all()


@pytest.mark.parametrize("rs", ["HRD", "HRR"])
@pytest.mark.parametrize("veld", ["DuitseDeelstaat", "IndicatieWoonplaatsVereiste"])
def test_hisbek_woonplaatsvelden_alleen_2011_tot_en_met_2014(demo_hisbek, rs, veld):
    df = demo_hisbek[rs].with_columns(pl.col("Bekostigingsjaar").cast(pl.Int64))
    buiten = df.filter(~pl.col("Bekostigingsjaar").is_between(2011, 2014))
    assert (buiten[veld] == "").all()


def test_definitief_herstelt_te_laat_aangeleverd(demo_star):
    feit = (
        demo_star["fact_deelname"]
        .join(demo_star["dim_levering"], on="levering")
        .filter(pl.col("Bekostigingsjaar") == 2025)
    )
    ti = feit.filter(pl.col("CodeBekostigingstatus").str.contains("ti"))
    per_soort = dict(ti.group_by("SoortLevering").len().rows())
    assert per_soort["DEFBEK"] < per_soort["VLPBEK"]
