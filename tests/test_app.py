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
        f'output = "{(tmp_path / "out").as_posix()}"\n'
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
