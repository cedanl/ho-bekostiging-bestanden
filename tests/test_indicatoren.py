import polars as pl
import pytest

from ho_bekostiging_bestanden import indicatoren as ind
from ho_bekostiging_bestanden.pipeline import verwerk_alles

from .conftest import analyse_regels, hisbek_regels, maak_regel, schrijf_bestand


def _star(tmp_path, bestanden):
    raw = tmp_path / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for naam, regels in bestanden.items():
        schrijf_bestand(raw, naam, regels)
    return verwerk_alles(raw, tmp_path / "prep", tmp_path / "out").star


@pytest.fixture
def star(tmp_path):
    return _star(
        tmp_path,
        {
            "VLPBEK_2025_20240115_99XX.csv": analyse_regels(),
            "DEFBEK_2025_20240715_99XX.csv": analyse_regels(
                statussen=("pi", "mv", "pi")
            ),
            "HISBEK_2024_20250301_99XX.csv": hisbek_regels(),
        },
    )


def _deelnames(star, soort):
    return ind.feiten(star, "fact_deelname", ind.actuele_leveringen(star, soort))


def test_feiten_alleen_eigen_instelling(star):
    df = _deelnames(star, ind.VOORLOPIG)
    assert df.height == 2
    assert set(df["BRIN"]) == {"99XX"}
    assert {"SoortLevering", "Opleidingsniveau", "Beoordeeld"} <= set(df.columns)


def test_trechter(star):
    assert ind.trechter(_deelnames(star, ind.VOORLOPIG)).rows() == [
        ("In bestand", 2),
        ("Beoordeeld", 2),
        ("Bekostigd", 1),
    ]


def test_trechter_telt_mv_niet_als_beoordeeld(tmp_path):
    regels = analyse_regels(statussen=("mv", "pi", "pi"))
    star = _star(tmp_path, {"VLPBEK_2025_20240115_99XX.csv": regels})
    df = ind.feiten(star, "fact_deelname", ind.actuele_leveringen(star, ind.VOORLOPIG))
    assert ind.trechter(df)["Aantal"].to_list() == [2, 1, 1]


def test_redenen_niet_bekostigd(star):
    redenen = ind.redenen_niet_bekostigd(_deelnames(star, ind.VOORLOPIG), star)
    assert sorted(redenen.select("Code", "Aantal").rows()) == [("na", 1), ("ti", 1)]
    assert set(redenen["Groep"]) == {"Status van de student", "Aanlevering"}


def test_per_opleiding(star):
    rij = ind.per_opleiding(_deelnames(star, ind.VOORLOPIG)).row(0, named=True)
    assert rij == {
        "Opleidingscode": "34001",
        "Opleidingsniveau": "HBO-BA",
        "Totaal": 2,
        "Bekostigd": 1,
        "AandeelBekostigd": 0.5,
    }


def test_voorlopig_vs_definitief(star):
    assert ind.voorlopig_vs_definitief(star).rows() == [(2025, "na,ti", "pi", 1)]


def test_historie(star):
    assert ind.historie(star).rows() == [
        (2023, "deelname", 1, 1),
        (2024, "deelname", 1, 0),
        (2024, "resultaat", 1, 1),
    ]


def test_zonder_defbek_en_hisbek(tmp_path):
    star = _star(tmp_path, {"VLPBEK_2025_20240115_99XX.csv": analyse_regels()})
    assert not ind.heeft_soort(star, ind.DEFINITIEF)
    assert ind.voorlopig_vs_definitief(star).is_empty()
    assert ind.historie(star).columns == [
        "Bekostigingsjaar",
        "Bron",
        "Totaal",
        "Bekostigd",
    ]
    assert ind.historie(star).is_empty()


def test_actuele_levering_is_nieuwste(tmp_path):
    oud = analyse_regels()
    nieuw = analyse_regels()
    nieuw[0] = maak_regel(
        "analyse", "VLP", BRIN="99XX", Bekostigingsjaar="2025", DatumAanmaak="20240315"
    )
    star = _star(
        tmp_path,
        {
            "VLPBEK_2025_20240115_99XX.csv": oud,
            "VLPBEK_2025_20240315_99XX.csv": nieuw,
        },
    )
    assert ind.actuele_leveringen(star, ind.VOORLOPIG) == ["VLPBEK_2025_20240315_99XX"]


def test_lege_invoer_geeft_lege_frames(tmp_path):
    star = _star(tmp_path, {})
    df = ind.feiten(star, "fact_deelname", [])
    assert df.is_empty()
    assert ind.trechter(df)["Aantal"].to_list() == [0, 0, 0]
    assert ind.redenen_niet_bekostigd(df, star).is_empty()
    assert ind.per_opleiding(df).is_empty()


def test_demo_heeft_alle_grafieken(demo_star):
    deelnames = ind.feiten(
        demo_star, "fact_deelname", ind.actuele_leveringen(demo_star, ind.DEFINITIEF)
    )
    assert ind.trechter(deelnames)["Aantal"][0] > 0
    assert not ind.redenen_niet_bekostigd(deelnames, demo_star).is_empty()
    assert not ind.voorlopig_vs_definitief(demo_star).is_empty()
    assert ind.historie(demo_star)["Bekostigingsjaar"].n_unique() == 4
    assert isinstance(ind.per_opleiding(deelnames), pl.DataFrame)
