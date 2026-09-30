"""End-to-end: elke combinatie van leveringen moet een volledig star schema geven."""

import pytest

from ho_bekostiging_bestanden.kwaliteit import STATUS_OK
from ho_bekostiging_bestanden.pipeline import DATAMODEL_MAP, verwerk_alles
from ho_bekostiging_bestanden.star import STAR_TABELLEN

from .conftest import analyse_regels, hisbek_regels, schrijf_bestand

BESTANDEN = {
    "vlpbek": ("VLPBEK_2025_20240115_99XX.csv", lambda: analyse_regels()),
    "defbek": (
        "DEFBEK_2025_20240715_99XX.csv",
        lambda: analyse_regels(statussen=("pi", "mv", "pi")),
    ),
    "hisbek": ("HISBEK_2024_20250301_99XX.csv", hisbek_regels),
}

SCENARIOS = {
    "alle leveringen": ["vlpbek", "defbek", "hisbek"],
    "zonder HISBEK": ["vlpbek", "defbek"],
    "alleen VLPBEK": ["vlpbek"],
    "alleen HISBEK": ["hisbek"],
}


def _raw(tmp_path, soorten):
    raw = tmp_path / "raw"
    raw.mkdir()
    for soort in soorten:
        naam, regels = BESTANDEN[soort]
        schrijf_bestand(raw, naam, regels())
    return raw


@pytest.mark.parametrize("soorten", SCENARIOS.values(), ids=SCENARIOS.keys())
def test_scenario_levert_volledig_star_schema(tmp_path, soorten):
    raw = _raw(tmp_path, soorten)
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.fouten == {}
    assert tuple(resultaat.star) == STAR_TABELLEN
    assert resultaat.star["dim_levering"].height == len(soorten)
    geschreven = {p.stem for p in (tmp_path / "out" / DATAMODEL_MAP).glob("*.parquet")}
    assert geschreven == set(STAR_TABELLEN)
    assert resultaat.status == STATUS_OK
    assert resultaat.meldingen.is_empty()


def test_fout_bestand_stopt_de_rest_niet(tmp_path):
    raw = _raw(tmp_path, ["vlpbek"])
    schrijf_bestand(
        raw, "DEFBEK_2025_20240715_99XX.csv", analyse_regels()[1:]
    )  # geen VLP
    (raw / "notities.txt").write_text("genegeerd", encoding="utf-8")
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert list(resultaat.fouten) == ["DEFBEK_2025_20240715_99XX.csv"]
    assert "VLP" in resultaat.fouten["DEFBEK_2025_20240715_99XX.csv"]
    assert resultaat.star["dim_levering"].height == 1


def test_lege_map(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.prepared_dirs == []
    assert tuple(resultaat.star) == STAR_TABELLEN
