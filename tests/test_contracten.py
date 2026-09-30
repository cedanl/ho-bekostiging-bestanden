import polars as pl

from ho_bekostiging_bestanden.contracten import GRAIN, KOPPELINGEN, controleer_star
from ho_bekostiging_bestanden.kwaliteit import ERNST_ERROR, MELDING_SCHEMA
from ho_bekostiging_bestanden.star import STAR_TABELLEN


def test_register_dekt_alle_tabellen():
    assert set(GRAIN) == set(STAR_TABELLEN)
    for k in KOPPELINGEN:
        assert k.feit in STAR_TABELLEN
        assert set(k.doelen) <= set(STAR_TABELLEN)


def test_demo_voldoet_aan_alle_contracten(demo_star):
    meldingen = controleer_star(demo_star)
    assert meldingen.schema == MELDING_SCHEMA
    assert meldingen.is_empty(), meldingen.to_dicts()


def test_een_dubbeling_een_lege_sleutel_een_wees(demo_star):
    star = dict(demo_star)
    opl = star["dim_opleiding"]
    star["dim_opleiding"] = pl.concat([opl, opl.head(1)])
    eerste = pl.int_range(pl.len()) == 0
    star["fact_resultaat"] = star["fact_resultaat"].with_columns(
        pl.when(eerste).then(None).otherwise(pl.col("BRIN")).alias("BRIN")
    )
    status = star["fact_status"]
    star["fact_status"] = pl.concat(
        [status, status.head(1).with_columns(pl.lit("zz").alias("Code"))]
    )
    meldingen = controleer_star(star)
    assert sorted(meldingen["Controle"].to_list()) == [
        "Koppeling",
        "Lege sleutel",
        "Uniciteit",
    ]
    assert set(meldingen["Recordsoort"]) == {
        "dim_opleiding",
        "fact_resultaat",
        "fact_status",
    }
    assert set(meldingen["Ernst"]) == {ERNST_ERROR}
