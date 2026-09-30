"""Regressietests voor de bevindingen uit de eindreview."""

import subprocess
from pathlib import Path

import polars as pl

from ho_bekostiging_bestanden import indicatoren as ind
from ho_bekostiging_bestanden.pipeline import run_pipeline, verwerk_alles
from ho_bekostiging_bestanden.stack import stack_prepared
from ho_bekostiging_bestanden.star import FEIT_ID, build_star

from .conftest import analyse_regels, schrijf_bestand

ROOT = Path(__file__).parents[1]


def test_uploads_in_demo_map_worden_door_git_genegeerd():
    """Echte uploads (met BSN's) mogen nooit per ongeluk gecommit worden."""
    uitkomst = subprocess.run(
        ["git", "check-ignore", "-q", "data/01-raw/demo/upload/DEFBEK_2025_x_99XX.csv"],
        cwd=ROOT,
        check=False,
    )
    assert uitkomst.returncode == 0


def test_dubbele_bestandsnaam_wordt_een_keer_verwerkt(tmp_path):
    raw = tmp_path / "raw"
    naam = "VLPBEK_2025_20240115_99XX.csv"
    schrijf_bestand(raw, naam, analyse_regels())
    schrijf_bestand(raw / "upload", naam, analyse_regels())
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.star["fact_deelname"].height == 3
    assert len(resultaat.prepared_dirs) == 1
    assert any("dubbel" in fout.lower() for fout in resultaat.fouten.values())


def test_vergelijkbare_jaren_alleen_bij_zelfde_jaar(tmp_path):
    raw = tmp_path / "raw"
    schrijf_bestand(raw, "VLPBEK_2026_20250115_99XX.csv", analyse_regels(jaar=2026))
    schrijf_bestand(raw, "DEFBEK_2025_20240715_99XX.csv", analyse_regels())
    star = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out").star
    assert ind.vergelijkbare_jaren(star) == []


def test_vergelijkbare_jaren_met_zelfde_jaar(tmp_path):
    raw = tmp_path / "raw"
    schrijf_bestand(raw, "VLPBEK_2025_20240115_99XX.csv", analyse_regels())
    schrijf_bestand(raw, "DEFBEK_2025_20240715_99XX.csv", analyse_regels())
    star = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out").star
    assert ind.vergelijkbare_jaren(star) == [2025]


def test_opnieuw_verwerken_laat_geen_oude_tabellen_achter(tmp_path):
    doel = tmp_path / "prep"
    naam = "VLPBEK_2025_20240115_99XX.csv"
    run_pipeline(schrijf_bestand(tmp_path / "a", naam, analyse_regels()), doel)
    zonder_brr = [r for r in analyse_regels() if not r.startswith("BRR")]
    run_pipeline(schrijf_bestand(tmp_path / "b", naam, zonder_brr), doel)
    assert not (doel / "BRR.parquet").exists()


def test_feit_id_stabiel_als_levering_wordt_toegevoegd(tmp_path):
    def prep(naam, regels):
        doel = tmp_path / "prep" / Path(naam).stem
        run_pipeline(schrijf_bestand(tmp_path / "raw", naam, regels), doel)
        return doel

    later = prep("VLPBEK_2025_20240115_99XX.csv", analyse_regels())
    eerder = prep("DEFBEK_2025_20240715_99XX.csv", analyse_regels())  # sorteert eerder
    alleen = build_star(stack_prepared([later]))["fact_deelname"]
    beide = build_star(stack_prepared([eerder, later]))["fact_deelname"]
    ids = beide.filter(pl.col("levering") == later.name)[FEIT_ID].sort()
    assert ids.to_list() == alleen[FEIT_ID].sort().to_list()
