"""Npuls-huisstijl: tokens zijn de enige bron voor kleuren en thema."""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

import _huisstijl as hs  # noqa: E402

HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


def test_kleur_uit_tokens():
    assert hs.kleur("npuls-blauw") == "#3D68EC"
    assert hs.kleur("licht-blauw") == "#D6E2FD"
    assert hs.kleur("grijs-200") == "#DCDCE0"


def test_feedbackkleur_fout_is_oranje():
    assert hs.feedback("fout") == hs.kleur("npuls-oranje")


def test_grafiekpalet_volgt_categorische_volgorde_zonder_geel():
    assert hs.grafiekpalet() == ["#3D68EC", "#DD784B", "#00AF81"]


def test_css_bevat_alle_tokenvariabelen_en_font():
    css = hs.css()
    for naam, waarde in hs.tokens()["css_variables"].items():
        if naam.startswith("--"):
            assert f"{naam}: {waarde};" in css, naam
    assert "Plus+Jakarta+Sans" in css


def test_streamlit_thema_volgt_tokens():
    with (ROOT / ".streamlit" / "config.toml").open("rb") as f:
        thema = tomllib.load(f)["theme"]
    assert thema["primaryColor"] == hs.kleur("npuls-blauw")
    assert thema["textColor"] == hs.kleur("npuls-zwart")
    assert thema["backgroundColor"] == hs.kleur("npuls-wit")
    assert thema["redColor"] == hs.feedback("fout")
    assert thema["yellowColor"] == hs.feedback("waarschuwing")
    assert thema["greenColor"] == hs.feedback("succes")
    assert thema["blueColor"] == hs.feedback("info")
    assert thema["chartCategoricalColors"] == hs.grafiekpalet()
    assert thema["sidebar"]["backgroundColor"] == hs.kleur("licht-blauw")
    assert thema["sidebar"]["secondaryBackgroundColor"] == hs.kleur("npuls-wit")
    assert "Plus Jakarta Sans" in thema["font"]


def test_geen_hardcoded_hexkleuren_in_app_code():
    bestanden = [*APP.glob("*.py"), *APP.glob("pages/*.py")]
    gevonden = {
        p.name: HEX.findall(p.read_text(encoding="utf-8"))
        for p in bestanden
        if HEX.search(p.read_text(encoding="utf-8"))
    }
    assert gevonden == {}


def test_opmaak_zet_raster_en_astekst_uit_tokens():
    import altair as alt
    import polars as pl

    spec = hs.opmaak(alt.Chart(pl.DataFrame({"x": [1]}), mark="bar")).to_dict()
    assert spec["config"]["axis"]["gridColor"] == hs.kleur("grijs-200")
    assert spec["config"]["axis"]["labelColor"] == hs.kleur("npuls-zwart")
