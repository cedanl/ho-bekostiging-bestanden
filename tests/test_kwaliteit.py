import polars as pl
import pytest

from ho_bekostiging_bestanden.kwaliteit import (
    ERNST_ERROR,
    ERNST_WARNING,
    MELDING_SCHEMA,
    RAPPORT_SCHEMA,
    STAR_BRON,
    STATUS_FAIL,
    STATUS_OK,
    STATUS_WARN,
    KwaliteitsFout,
    bouw_rapport,
    lees_status,
    melding,
    meldingen_frame,
    met_bron,
    poort,
    schrijf_rapport,
    status,
)
from ho_bekostiging_bestanden.stack import LABEL_COL


def _m(ernst: str, controle: str = "Eén rij") -> dict:
    return melding(controle, "VLP", "Verwacht 1 rij, gevonden 2", ernst, 2)


def test_status_per_ernst():
    assert status(meldingen_frame([])) == STATUS_OK
    assert status(meldingen_frame([_m(ERNST_WARNING)])) == STATUS_WARN
    assert status(meldingen_frame([_m(ERNST_WARNING), _m(ERNST_ERROR)])) == STATUS_FAIL


def test_meldingen_frame_heeft_vast_schema():
    assert meldingen_frame([]).schema == MELDING_SCHEMA
    assert met_bron(meldingen_frame([_m(ERNST_ERROR)]), "x").schema == RAPPORT_SCHEMA


def test_poort_gooit_alleen_bij_fail():
    poort(met_bron(meldingen_frame([_m(ERNST_WARNING)]), "x"), "zie x")
    fout = met_bron(meldingen_frame([_m(ERNST_WARNING), _m(ERNST_ERROR)]), "x")
    with pytest.raises(KwaliteitsFout, match="1 error") as info:
        poort(fout, "zie x")
    assert info.value.meldingen["Ernst"].to_list() == [ERNST_ERROR]


def test_rapport_round_trip_met_niet_ascii(tmp_path):
    dim_levering = pl.DataFrame({LABEL_COL: ["lev_a", "lev_b"]})
    meldingen = pl.concat(
        [
            met_bron(meldingen_frame([_m(ERNST_ERROR)]), "lev_a"),
            met_bron(meldingen_frame([_m(ERNST_WARNING)]), STAR_BRON),
        ]
    )
    rapport = bouw_rapport(meldingen, dim_levering, fouten_toegestaan=True)
    assert rapport["status"] == STATUS_FAIL
    assert (rapport["total_errors"], rapport["total_warnings"]) == (1, 1)
    assert rapport["fouten_toegestaan"] is True
    assert [lev["status"] for lev in rapport["leveringen"]] == [STATUS_FAIL, STATUS_OK]
    assert rapport["leveringen"][0]["meldingen"][0]["controle"] == "Eén rij"
    assert rapport["star"]["status"] == STATUS_WARN
    pad = schrijf_rapport(rapport, tmp_path)
    assert "Eén rij" in pad.read_text(encoding="utf-8")
    assert lees_status(pad) == (STATUS_FAIL, 1)
