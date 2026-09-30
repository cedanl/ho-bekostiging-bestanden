import polars as pl
import pytest

from ho_bekostiging_bestanden.metadata import (
    SCHEMA_DIR,
    load_codelijst,
    load_schema,
    schema_meta,
)

SCHEMAS = ["analyse", "hisbek"]
_LIJST_SLEUTELS = [
    "date_fields",
    "bool_fields",
    "int_fields",
    "float_fields",
    "nvt_fields",
    "required_fields",
]


@pytest.mark.parametrize("naam", SCHEMAS)
def test_schema_laadt_met_recordsoort_eerst(naam):
    schema = load_schema(naam)
    assert {"VLP", "SLR"} <= set(schema)
    for rs, spec in schema.items():
        assert spec["fields"][0] == "Recordsoort", rs
        assert len(spec["fields"]) == len(set(spec["fields"])), rs


@pytest.mark.parametrize("naam", SCHEMAS)
def test_typevelden_bestaan_in_fields(naam):
    for rs, spec in load_schema(naam).items():
        velden = set(spec["fields"])
        for sleutel in _LIJST_SLEUTELS:
            assert set(spec.get(sleutel, [])) <= velden, (rs, sleutel)
        assert set(spec.get("codelijsten", {})) <= velden, rs


@pytest.mark.parametrize("naam", SCHEMAS)
def test_codelijsten_uit_schema_bestaan(naam):
    for spec in load_schema(naam).values():
        for lijst in spec.get("codelijsten", {}).values():
            assert (SCHEMA_DIR / f"{lijst}.csv").exists(), lijst


def test_veldaantallen_volgens_pve():
    analyse = load_schema("analyse")
    assert len(analyse["BLB"]["fields"]) == 21
    assert len(analyse["BRD"]["fields"]) == 25
    assert len(analyse["BRR"]["fields"]) == 24
    hisbek = load_schema("hisbek")
    assert len(hisbek["HRD"]["fields"]) == 30
    assert len(hisbek["HRR"]["fields"]) == 27


def test_schema_meta():
    assert schema_meta("analyse")["schema_version"] == "26.3.1"


def test_onbekend_schema_geeft_fout():
    with pytest.raises(FileNotFoundError):
        load_schema("bestaat_niet")


def test_bekostigingstatus_compleet():
    df = load_codelijst("bekostigingstatus")
    assert df.height == 34
    assert df["Code"].n_unique() == 34
    assert df["Groep"].null_count() == 0
    assert set(df["Bekostigd"].unique()) == {"J", "N"}
    bekostigd = set(df.filter(pl.col("Bekostigd") == "J")["Code"])
    assert bekostigd == {"pi", "pd", "pg", "pb", "pm", "po"}


def test_codelijst_kolommen_zijn_tekst():
    df = load_codelijst("opleidingsfase")
    assert df.schema["Code"] == pl.Utf8
    assert "1" in df["Code"].to_list()
