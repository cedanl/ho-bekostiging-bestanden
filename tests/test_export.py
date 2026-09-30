import polars as pl
import pytest

from ho_bekostiging_bestanden.decode import decode_frames
from ho_bekostiging_bestanden.export import export_frames
from ho_bekostiging_bestanden.ingest import read_multi_record_csv


@pytest.mark.parametrize("fmt", ["parquet", "csv"])
def test_export_gedecodeerde_frames(tmp_path, vlpbek_bestand, fmt):
    frames = decode_frames(read_multi_record_csv(vlpbek_bestand, "analyse"), "analyse")
    paden = export_frames(frames, tmp_path / "uit", fmt=fmt)
    assert {p.name for p in paden} >= {f"BRD.{fmt}", f"VLP.{fmt}"}
    lezer = pl.read_parquet if fmt == "parquet" else pl.read_csv
    assert lezer(tmp_path / "uit" / f"BRD.{fmt}").height == 3


def test_onbekend_formaat(tmp_path):
    with pytest.raises(ValueError, match="Onbekend formaat"):
        export_frames({}, tmp_path, fmt="xlsx")  # type: ignore
