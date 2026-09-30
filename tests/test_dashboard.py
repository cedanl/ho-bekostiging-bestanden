import re
import shutil
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ho_bekostiging_bestanden.pipeline import verwerk_alles

from .conftest import DEMO_RAW

APP = Path(__file__).parents[1] / "app"
sys.path.insert(0, str(APP))

from _chart_docs import CHART_DOCS  # noqa: E402
from _utils import CONFIG_ENV  # noqa: E402

TIMEOUT = 60


def _config(tmp_path, monkeypatch, raw: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        "[data]\n"
        f'raw = "{raw.as_posix()}"\n'
        f'prepared = "{(tmp_path / "prep").as_posix()}"\n'
        f'output = "{(tmp_path / "out").as_posix()}"\n'
    )
    monkeypatch.setenv(CONFIG_ENV, str(config))


def _dashboard() -> AppTest:
    return AppTest.from_file(
        str(APP / "pages" / "dashboard.py"), default_timeout=TIMEOUT
    )


def test_elke_grafiek_heeft_toelichting():
    bron = (APP / "pages" / "dashboard.py").read_text(encoding="utf-8")
    gebruikt = set(re.findall(r'chart_help\("(\w+)"\)', bron))
    assert gebruikt == set(CHART_DOCS)
    for sleutel, doc in CHART_DOCS.items():
        assert {"titel", "variabelen", "manipulatie"} <= set(doc), sleutel


def test_dashboard_zonder_data(tmp_path, monkeypatch):
    _config(tmp_path, monkeypatch, DEMO_RAW)
    at = _dashboard().run()
    assert not at.exception
    assert at.warning


def test_dashboard_met_demo(tmp_path, monkeypatch):
    _config(tmp_path, monkeypatch, DEMO_RAW)
    verwerk_alles(DEMO_RAW, tmp_path / "prep", tmp_path / "out")
    at = _dashboard().run()
    assert not at.exception
    assert len(at.tabs) == 5


@pytest.mark.parametrize(
    "bestand",
    ["VLPBEK_2025_20240115_99XX.csv", "HISBEK_2024_20250301_99XX.csv"],
    ids=["alleen VLPBEK", "alleen HISBEK"],
)
def test_dashboard_met_een_levering(tmp_path, monkeypatch, bestand):
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copy(DEMO_RAW / bestand, raw / bestand)
    _config(tmp_path, monkeypatch, raw)
    verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    at = _dashboard().run()
    assert not at.exception
    assert at.info  # uitleg bij de grafieken waarvoor data ontbreekt


def test_redenen_zonder_deelnames_claimt_niet_alles_bekostigd(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copy(DEMO_RAW / "HISBEK_2024_20250301_99XX.csv", raw)
    _config(tmp_path, monkeypatch, raw)
    verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    at = _dashboard().run()
    teksten = " ".join(i.value for i in at.info)
    assert "Alle beoordeelde deelnames" not in teksten
    assert "Geen deelnames in deze selectie" in teksten


def test_voorlopig_definitief_verschillende_jaren(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    for naam in ["VLPBEK_2026_20250115_99XX.csv", "DEFBEK_2025_20240715_99XX.csv"]:
        shutil.copy(DEMO_RAW / naam, raw)
    _config(tmp_path, monkeypatch, raw)
    verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    at = _dashboard().run()
    teksten = " ".join(i.value for i in at.info)
    assert "Geen statuswijzigingen" not in teksten
    assert "hetzelfde jaar" in teksten
