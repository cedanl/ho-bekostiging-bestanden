import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ho_bekostiging_bestanden.star import STAR_TABELLEN

from .conftest import DEMO_RAW

APP = Path(__file__).parents[1] / "app"
sys.path.insert(0, str(APP))

from _tabel_docs import TABEL_DOCS  # noqa: E402
from _utils import CONFIG_ENV  # noqa: E402

TIMEOUT = 60


@pytest.fixture
def app_config(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text(
        "[data]\n"
        f'raw = "{DEMO_RAW.as_posix()}"\n'
        f'prepared = "{(tmp_path / "prep").as_posix()}"\n'
        f'output = "{(tmp_path / "out").as_posix()}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(CONFIG_ENV, str(config))
    return tmp_path


def _pagina(naam: str) -> AppTest:
    return AppTest.from_file(str(APP / "pages" / f"{naam}.py"), default_timeout=TIMEOUT)


def test_tabel_docs_compleet():
    assert set(TABEL_DOCS) == set(STAR_TABELLEN)
    for naam, doc in TABEL_DOCS.items():
        assert {"titel", "wat", "bron"} <= set(doc), naam


def test_home_toont_bestanden_en_verwerkt(app_config):
    at = _pagina("home").run()
    assert not at.exception
    assert at.dataframe[0].value.shape[0] == 4
    at.button(key="verwerk_alles").click().run()
    assert not at.exception
    assert at.success
    assert (app_config / "out" / "datamodel" / "fact_deelname.parquet").exists()


def test_resultaten_zonder_verwerking(app_config):
    at = _pagina("resultaten").run()
    assert not at.exception
    assert at.warning


def test_resultaten_na_verwerking(app_config):
    _pagina("home").run().button(key="verwerk_alles").click().run()
    at = _pagina("resultaten").run()
    assert not at.exception
    assert at.selectbox(key="resultaten_tabel").options[0] in STAR_TABELLEN


def _config_met(tmp_path, monkeypatch, extra: str = "") -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        "[data]\n"
        f'raw = "{DEMO_RAW.as_posix()}"\n'
        f'prepared = "{(tmp_path / "prep").as_posix()}"\n'
        f'output = "{(tmp_path / "out").as_posix()}"\n' + extra,
        encoding="utf-8",
    )
    monkeypatch.setenv(CONFIG_ENV, str(config))


def test_home_zonder_sleutel_legt_uit_en_verwerkt_niet(tmp_path, monkeypatch):
    _config_met(tmp_path, monkeypatch)
    monkeypatch.delenv("EENCIJFERHO_ENCRYPT_KEY")
    at = _pagina("home").run()
    assert not at.exception
    assert any("EENCIJFERHO_ENCRYPT_KEY" in e.value for e in at.error)
    assert at.button(key="verwerk_alles").disabled


def test_home_met_demo_sleutel_waarschuwt(tmp_path, monkeypatch):
    demo = "demo-" + "d" * 70
    _config_met(tmp_path, monkeypatch, f'\n[security]\ndemo_sleutel = "{demo}"\n')
    monkeypatch.delenv("EENCIJFERHO_ENCRYPT_KEY")
    at = _pagina("home").run()
    assert any("demo-sleutel" in w.value.lower() for w in at.warning)
    at.button(key="verwerk_alles").click().run()
    assert not at.exception
    assert (tmp_path / "out" / "datamodel" / "dim_persoon.parquet").exists()


def test_standaardconfig_heeft_demo_sleutel_van_voldoende_lengte():
    import tomllib

    config = tomllib.loads((APP / "config.toml").read_text(encoding="utf-8"))
    assert len(config["security"]["demo_sleutel"].encode()) >= 64


def test_home_pseudonimisering_uit_zonder_sleutel(tmp_path, monkeypatch):
    _config_met(tmp_path, monkeypatch)
    monkeypatch.delenv("EENCIJFERHO_ENCRYPT_KEY")
    at = _pagina("home").run()
    assert at.checkbox(key="pseudonimiseer").value is True
    at.checkbox(key="pseudonimiseer").uncheck().run()
    assert not at.button(key="verwerk_alles").disabled
    assert any("leesbaar" in w.value for w in at.warning)
    at.button(key="verwerk_alles").click().run()
    assert not at.exception
    assert (tmp_path / "out" / "datamodel" / "dim_persoon.parquet").exists()
