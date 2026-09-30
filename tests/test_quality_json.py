import hashlib
import json
from importlib.resources import files

import jsonschema
import polars as pl
import pytest

from ho_bekostiging_bestanden.kwaliteit import QUALITY_JSON
from ho_bekostiging_bestanden.pipeline import verwerk_alles

from .conftest import DEMO_RAW

SCHEMA = json.loads(
    files("ho_bekostiging_bestanden.metadata")
    .joinpath("quality.schema.json")
    .read_text(encoding="utf-8")
)


def _rapport(uit):
    return json.loads((uit / QUALITY_JSON).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    basis = tmp_path_factory.mktemp("quality")
    verwerk_alles(DEMO_RAW, basis / "prep", basis / "out", pseudonimiseer=False)
    return basis, _rapport(basis / "out")


def test_demo_rapport_valideert_tegen_schema(demo):
    _, rapport = demo
    jsonschema.validate(rapport, SCHEMA)
    assert rapport["schema_version"] == 1
    assert rapport["provenance"]["pakketversie"]


def test_sha256_per_levering_klopt(demo):
    _, rapport = demo
    for lev in rapport["leveringen"]:
        bron = DEMO_RAW / lev["bestandsnaam"]
        assert lev["sha256"] == hashlib.sha256(bron.read_bytes()).hexdigest()


def test_dekking_telt_rijen_per_levering_en_recordsoort(demo):
    basis, rapport = demo
    label = "VLPBEK_2025_20240115_99XX"
    brd = next(
        d
        for d in rapport["dekking"]
        if d["recordsoort"] == "BRD" and d["levering"] == label
    )
    verwacht = pl.read_parquet(basis / "prep" / label / "BRD.parquet").height
    assert brd["rijen"] == verwacht
    # HISBEK kent geen BRD: die combinatie hoort er niet in.
    assert not any(
        d["levering"].startswith("HISBEK") and d["recordsoort"] == "BRD"
        for d in rapport["dekking"]
    )


def test_lege_map_valideert_tegen_schema(tmp_path):
    (tmp_path / "raw").mkdir()
    verwerk_alles(tmp_path / "raw", tmp_path / "prep", tmp_path / "out")
    rapport = _rapport(tmp_path / "out")
    jsonschema.validate(rapport, SCHEMA)
    assert rapport["leveringen"] == []
    assert rapport["dekking"] == []


def test_schema_is_strikt(demo):
    _, rapport = demo
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**rapport, "onbekend_veld": 1}, SCHEMA)
