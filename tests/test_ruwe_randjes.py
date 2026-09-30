"""Regressietests voor de kleine bugs en ruwe randjes uit de eindreview."""

import sys
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from ho_bekostiging_bestanden import indicatoren as ind
from ho_bekostiging_bestanden.cli import main
from ho_bekostiging_bestanden.pipeline import (
    onherkende_bestanden,
    run_pipeline,
    run_star,
    verwerk_alles,
)

from .conftest import analyse_regels, hisbek_regels, maak_regel, schrijf_bestand

ROOT = Path(__file__).parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

import _utils  # noqa: E402


def test_star_op_map_zonder_parquet_geeft_duidelijke_fout(tmp_path, vlpbek_bestand):
    doel = tmp_path / "prep"
    run_pipeline(vlpbek_bestand, doel, fmt="csv")
    with pytest.raises(ValueError, match="Parquet"):
        run_star([doel], tmp_path / "out")


def test_levering_zonder_aanmaakdatum_is_niet_de_nieuwste():
    star = {
        "dim_levering": pl.DataFrame(
            {
                "levering": ["zonder_datum", "met_datum"],
                "SoortLevering": ["VLPBEK", "VLPBEK"],
                "Bekostigingsjaar": [2025, 2025],
                "DatumAanmaak": [None, date(2024, 1, 15)],
            },
            schema_overrides={"DatumAanmaak": pl.Date},
        )
    }
    assert ind.actuele_leveringen(star, ind.VOORLOPIG) == ["met_datum"]


def test_historie_telt_mv_niet_mee(tmp_path):
    regels = hisbek_regels()
    extra = regels[1].replace("|2023|", "|2023|", 1).replace("|pi|", "|mv|", 1)
    extra = extra.replace("|J|mv|", "|N|mv|", 1)
    regels.insert(2, extra)
    regels[-1] = maak_regel("hisbek", "SLR", AantalHRDrecords="3", AantalHRRrecords="1")
    raw = tmp_path / "raw"
    schrijf_bestand(raw, "HISBEK_2024_20250301_99XX.csv", regels)
    star = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out").star
    rij_2023 = ind.historie(star).filter(pl.col("Bekostigingsjaar") == 2023).row(0)
    assert rij_2023 == (2023, "deelname", 1, 1)


def test_label_vult_ontbrekende_waarden():
    df = pl.DataFrame({"a": ["34001", None], "b": [None, "HBO-BA"]})
    labels = df.select(ind.label("{} ({})", "a", "b"))["label"].to_list()
    assert labels == ["34001 (onbekend)", "onbekend (HBO-BA)"]


def test_onherkende_csv_bestanden_worden_gevonden(tmp_path):
    raw = tmp_path / "raw"
    schrijf_bestand(raw, "VLPBEK_2025_20240115_99XX.csv", analyse_regels())
    schrijf_bestand(raw, "VLPBEK_2025_20240115_99XX (1).csv", analyse_regels())
    (raw / "notities.txt").write_text("geen csv")
    assert [p.name for p in onherkende_bestanden(raw)] == [
        "VLPBEK_2025_20240115_99XX (1).csv"
    ]


def test_cli_toont_nette_fout_zonder_traceback(tmp_path, monkeypatch, capsys):
    onbekend = tmp_path / "RO_27DV_20240731_20260324.csv"
    onbekend.write_text("VLP|x")
    monkeypatch.setattr(sys, "argv", ["ho", "verwerk", str(onbekend), str(tmp_path)])
    with pytest.raises(SystemExit) as uitkomst:
        main()
    assert uitkomst.value.code == 1
    fout = capsys.readouterr().err
    assert "Onbekend bestandstype" in fout
    assert "Traceback" not in fout


def test_relatieve_configpaden_gaan_uit_van_de_repo(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text(
        '[data]\nraw = "data/01-raw/demo"\nprepared = "p"\noutput = "o"\n'
    )
    monkeypatch.setenv(_utils.CONFIG_ENV, str(config))
    monkeypatch.chdir(tmp_path)
    assert _utils.raw_dir() == ROOT / "data" / "01-raw" / "demo"
    assert _utils.raw_dir().exists()


def test_geen_verouderde_use_container_width_in_app():
    bestanden = [*APP.glob("*.py"), *APP.glob("pages/*.py")]
    assert [
        p.name for p in bestanden if "use_container_width" in p.read_text("utf-8")
    ] == []


def test_altair_is_directe_dependency():
    import tomllib

    deps = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
        "dependencies"
    ]
    assert any(d.startswith("altair") for d in deps)
