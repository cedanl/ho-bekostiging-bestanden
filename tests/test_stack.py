import polars as pl
import pytest

from ho_bekostiging_bestanden.stack import stack_prepared


def _schrijf(map_, naam, df):
    map_.mkdir(parents=True, exist_ok=True)
    df.write_parquet(map_ / f"{naam}.parquet")


def test_stack_voegt_levering_toe_en_concateneert(tmp_path):
    _schrijf(tmp_path / "A", "BRD", pl.DataFrame({"x": [1, 2]}))
    _schrijf(tmp_path / "B", "BRD", pl.DataFrame({"x": [3], "y": ["extra"]}))
    _schrijf(tmp_path / "B", "HRD", pl.DataFrame({"z": [9]}))
    stacked = stack_prepared([tmp_path / "A", tmp_path / "B"])
    assert stacked["BRD"].columns[0] == "levering"
    assert stacked["BRD"]["levering"].to_list() == ["A", "A", "B"]
    assert stacked["BRD"]["y"].to_list() == [None, None, "extra"]
    assert stacked["HRD"].height == 1


def test_stack_leeg():
    assert stack_prepared([]) == {}


def test_stack_ontbrekende_map(tmp_path):
    with pytest.raises(FileNotFoundError):
        stack_prepared([tmp_path / "bestaat_niet"])


def test_stack_labels_moeten_passen(tmp_path):
    (tmp_path / "A").mkdir()
    with pytest.raises(ValueError):
        stack_prepared([tmp_path / "A"], labels=["a", "b"])
