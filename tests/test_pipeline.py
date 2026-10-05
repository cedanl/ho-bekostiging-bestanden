import hashlib
import json
from datetime import date

import polars as pl
import pytest

from ho_bekostiging_bestanden.kwaliteit import (
    QUALITY_JSON,
    STATUS_FAIL,
    STATUS_OK,
    STATUS_WARN,
    KwaliteitsFout,
)
from ho_bekostiging_bestanden.pipeline import (
    LEVERING,
    VALIDATIE,
    detect_levering,
    run_pipeline,
    run_star,
    verwerk_alles,
)

from .conftest import analyse_regels, schrijf_bestand


def test_eigen_bestanden_in_doelmap_blijven_staan(tmp_path, vlpbek_bestand):
    """Een verkeerd gekozen doelmap mag geen bestanden van de gebruiker wissen."""
    doel = tmp_path / "doel"
    doel.mkdir()
    eigen = [doel / "eigen.parquet", doel / "notities.csv"]
    for pad in eigen:
        pad.write_text("van de gebruiker", encoding="utf-8")
    run_pipeline(vlpbek_bestand, doel)
    assert all(pad.exists() for pad in eigen)


def test_tabel_uit_eerdere_verwerking_wordt_opgeruimd(
    tmp_path, vlpbek_bestand, hisbek_bestand
):
    """Een recordsoort die de nieuwe levering niet heeft, blijft niet hangen."""
    doel = tmp_path / "doel"
    run_pipeline(hisbek_bestand, doel)
    run_pipeline(vlpbek_bestand, doel, fmt="csv")
    assert not list(doel.glob("HRD.*"))
    assert not list(doel.glob("*.parquet"))


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
        "Sha256": hashlib.sha256(vlpbek_bestand.read_bytes()).hexdigest(),
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


def _fout_bestand(map_):
    regels = analyse_regels()
    regels.insert(1, "XYZ|x")  # onbekende recordsoort → error
    return schrijf_bestand(map_, "VLPBEK_2025_20240115_99XX.csv", regels)


def _rapport(uit):
    return json.loads((uit / QUALITY_JSON).read_text(encoding="utf-8"))


def test_run_pipeline_poort_na_wegschrijven(tmp_path):
    doel = tmp_path / "prep"
    with pytest.raises(KwaliteitsFout, match="1 error"):
        run_pipeline(_fout_bestand(tmp_path / "raw"), doel)
    validatie = pl.read_parquet(doel / f"{VALIDATIE}.parquet")
    assert validatie["Ernst"].to_list() == ["error"]


def test_run_pipeline_fouten_toegestaan(tmp_path):
    frames = run_pipeline(
        _fout_bestand(tmp_path / "raw"), tmp_path / "prep", fail_on_errors=False
    )
    assert frames[VALIDATIE].height == 1


def test_run_star_schrijft_quality_json_en_gooit(tmp_path):
    prep = tmp_path / "prep" / "lev"
    run_pipeline(_fout_bestand(tmp_path / "raw"), prep, fail_on_errors=False)
    uit = tmp_path / "out"
    with pytest.raises(KwaliteitsFout):
        run_star([prep], uit)
    assert (uit / "datamodel" / "fact_deelname.parquet").exists()
    rapport = _rapport(uit)
    assert rapport["status"] == STATUS_FAIL
    assert rapport["fouten_toegestaan"] is False
    assert rapport["leveringen"][0]["levering"] == "lev"


def test_verouderde_prepared_map_is_fail(tmp_path, vlpbek_bestand):
    prep = tmp_path / "prep" / "oud"
    run_pipeline(vlpbek_bestand, prep)
    pad = prep / f"{VALIDATIE}.parquet"
    pl.read_parquet(pad).drop("Ernst").write_parquet(pad)
    run_star([prep], tmp_path / "out", fail_on_errors=False)
    rapport = _rapport(tmp_path / "out")
    assert rapport["status"] == STATUS_FAIL
    assert "verwerk" in rapport["leveringen"][0]["meldingen"][0]["melding"]


def test_verwerk_alles_gooit_niet_maar_meldt(tmp_path):
    raw = tmp_path / "raw"
    _fout_bestand(raw)
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.status == STATUS_FAIL
    assert resultaat.meldingen["Bron"].to_list() == ["VLPBEK_2025_20240115_99XX"]


def test_verwerk_alles_lege_map_is_ok(tmp_path):
    (tmp_path / "raw").mkdir()
    resultaat = verwerk_alles(tmp_path / "raw", tmp_path / "prep", tmp_path / "out")
    assert resultaat.status == STATUS_OK
    assert _rapport(tmp_path / "out")["leveringen"] == []


def test_alleen_warnings_is_warn(tmp_path):
    raw = tmp_path / "raw"
    # Jaar in de bestandsnaam wijkt af van de VLP → warning.
    schrijf_bestand(raw, "VLPBEK_2024_20240115_99XX.csv", analyse_regels())
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.status == STATUS_WARN


def test_star_contractbreuk_is_fail(tmp_path, vlpbek_bestand, monkeypatch):
    from ho_bekostiging_bestanden import contracten

    prep = tmp_path / "prep" / "lev"
    run_pipeline(vlpbek_bestand, prep)
    # Eén contract dat altijd één error oplevert.
    altijd_fout = contracten.Controle(
        "Test", "error", lambda star: iter([("dim_levering", "x", 1)])
    )
    monkeypatch.setattr(contracten, "CONTROLES", (altijd_fout,))
    with pytest.raises(KwaliteitsFout):
        run_star([prep], tmp_path / "out")
    rapport = _rapport(tmp_path / "out")
    assert rapport["star"]["status"] == STATUS_FAIL
    assert rapport["leveringen"][0]["status"] == STATUS_OK


def test_onverwerkbaar_bestand_is_error_in_rapport(tmp_path):
    raw = tmp_path / "raw"
    schrijf_bestand(raw, "VLPBEK_2025_20240115_99XX.csv", analyse_regels())
    # DEFBEK zonder VLP kan niet verwerkt worden.
    schrijf_bestand(raw, "DEFBEK_2025_20240715_99XX.csv", analyse_regels()[1:])
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.status == STATUS_FAIL
    rapport = _rapport(tmp_path / "out")
    defbek = next(
        lev
        for lev in rapport["leveringen"]
        if lev["levering"] == "DEFBEK_2025_20240715_99XX"
    )
    assert defbek["status"] == STATUS_FAIL
    assert "VLP" in defbek["meldingen"][0]["melding"]


def test_dubbel_bestand_is_warning(tmp_path):
    raw = tmp_path / "raw"
    schrijf_bestand(raw, "VLPBEK_2025_20240115_99XX.csv", analyse_regels())
    schrijf_bestand(raw / "upload", "VLPBEK_2025_20240115_99XX.csv", analyse_regels())
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.status == STATUS_WARN
    assert resultaat.meldingen["Ernst"].to_list() == ["warning"]


def test_dubbele_leveringslabels_zijn_invoerfout(tmp_path, vlpbek_bestand):
    a = tmp_path / "a" / "lev"
    b = tmp_path / "b" / "lev"
    run_pipeline(vlpbek_bestand, a)
    run_pipeline(vlpbek_bestand, b)
    with pytest.raises(ValueError, match="lev"):
        run_star([a, b], tmp_path / "out")
