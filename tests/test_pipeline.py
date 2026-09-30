from datetime import date

import polars as pl
import pytest

from ho_bekostiging_bestanden.pipeline import (
    LEVERING,
    VALIDATIE,
    detect_levering,
    run_pipeline,
)


def test_detect_levering():
    assert detect_levering("x/DEFBEK_2025_20240715_99XX.CSV") == "DEFBEK"
    assert detect_levering("x/RO_27DV_20240731_20260324.csv") is None


def test_run_pipeline_vlpbek(tmp_path, vlpbek_bestand):
    doel = tmp_path / "prep"
    frames = run_pipeline(vlpbek_bestand, doel)
    geschreven = {p.stem for p in doel.glob("*.parquet")}
    assert geschreven == {"VLP", "BLB", "BRD", "BRR", "SLR", LEVERING, VALIDATIE}
    assert "_MELDINGEN" not in frames
    levering = pl.read_parquet(doel / f"{LEVERING}.parquet").row(0, named=True)
    assert levering == {
        "SoortLevering": "VLPBEK",
        "Bekostigingsjaar": 2025,
        "DatumAanmaak": date(2024, 1, 15),
        "BrinOntvanger": "99XX",
        "Bestandsnaam": "VLPBEK_2025_20240115_99XX.csv",
        "SchemaVersie": "26.3.1",
        "Gepseudonimiseerd": True,
    }
    assert frames[VALIDATIE].height == 0


def test_run_pipeline_hisbek(tmp_path, hisbek_bestand):
    frames = run_pipeline(hisbek_bestand, tmp_path / "prep")
    assert frames[LEVERING]["Bekostigingsjaar"][0] == 2024
    assert frames["HRD"].height == 2


def test_run_pipeline_csv(tmp_path, vlpbek_bestand):
    run_pipeline(vlpbek_bestand, tmp_path / "prep", fmt="csv")
    assert pl.read_csv(tmp_path / "prep" / "BRD.csv").height == 3


def test_onbekend_bestand(tmp_path):
    pad = tmp_path / "RO_27DV_20240731_20260324.csv"
    pad.write_text("VLP|x", encoding="utf-8")
    with pytest.raises(ValueError, match="Onbekend bestandstype"):
        run_pipeline(pad, tmp_path / "prep")
