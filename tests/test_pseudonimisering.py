"""BSN-pseudonimisering gelijk aan 1cijferho: koppelen met 1CHO (#17)."""

import sys

import polars as pl
import pytest

from ho_bekostiging_bestanden.cli import main
from ho_bekostiging_bestanden.pipeline import run_pipeline, verwerk_alles
from ho_bekostiging_bestanden.pseudonimisering import (
    SLEUTEL_ENV,
    laad_sleutel,
    pseudoniem,
)

from .conftest import TEST_SLEUTEL, analyse_regels, schrijf_bestand

# Berekend met de échte 1cijferho-code: eencijferho.utils.pseudonymizer.
# pseudonymize_value(load_key(TEST_SLEUTEL), waarde), cedanl/1cijferho main f6a0990.
REFERENTIE_1CIJFERHO = {
    "012345678": "9dbad58fb52703c363abae6b5ca53915ad02778149fb1df5c8ea218b9fbc7cac",
    "700010001": "72bb72a4683bd0ef99f5117fabea08eac2b849ca3473ac450915e060495f4efc",
    "800010002": "39bfd58e00941101897cca617ad6862930f90c17dbfbf19246399d6d998a422c",
}


@pytest.mark.parametrize("waarde,verwacht", REFERENTIE_1CIJFERHO.items())
def test_pseudoniem_gelijk_aan_1cijferho(waarde, verwacht):
    assert pseudoniem(laad_sleutel(TEST_SLEUTEL), waarde) == verwacht


@pytest.mark.parametrize("waarde", [None, ""])
def test_lege_waarde_blijft_leeg(waarde):
    assert pseudoniem(laad_sleutel(TEST_SLEUTEL), waarde) is None


def test_sleutel_uit_omgeving_bestand_en_te_kort(tmp_path, monkeypatch):
    assert laad_sleutel() == TEST_SLEUTEL.encode()  # autouse-fixture zet de env-var
    bestand = tmp_path / "sleutel.txt"
    bestand.write_text(TEST_SLEUTEL + "\n")
    assert laad_sleutel(sleutelbestand=bestand) == TEST_SLEUTEL.encode()
    with pytest.raises(ValueError, match="te kort"):
        laad_sleutel("kort")
    monkeypatch.delenv(SLEUTEL_ENV)
    with pytest.raises(ValueError, match=SLEUTEL_ENV):
        laad_sleutel()


def test_prepared_bevat_geen_leesbaar_bsn(tmp_path, vlpbek_bestand):
    doel = tmp_path / "prep"
    frames = run_pipeline(vlpbek_bestand, doel)
    for pad in doel.glob("*.parquet"):
        df = pl.read_parquet(pad)
        tekst = df.select(pl.col(pl.Utf8)).write_csv()
        assert "700010001" not in tekst and "800010001" not in tekst, pad.name
    assert frames["BRD"]["Burgerservicenummer"][0] == REFERENTIE_1CIJFERHO["700010001"]


def test_star_koppelsleutels_zijn_1cijferho_pseudoniemen(tmp_path, vlpbek_bestand):
    raw = vlpbek_bestand.parent
    star = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out").star
    persoon = star["dim_persoon"]
    assert REFERENTIE_1CIJFERHO["700010001"] in persoon["Burgerservicenummer"].to_list()
    # Persoon zonder BSN: _persoon_id is het pseudoniem van het onderwijsnummer.
    assert REFERENTIE_1CIJFERHO["800010002"] in persoon["_persoon_id"].to_list()


def test_zonder_sleutel_geen_verwerking(tmp_path, vlpbek_bestand, monkeypatch):
    monkeypatch.delenv(SLEUTEL_ENV)
    with pytest.raises(ValueError, match=SLEUTEL_ENV):
        run_pipeline(vlpbek_bestand, tmp_path / "prep")
    assert not (tmp_path / "prep").exists()


def test_cli_zonder_sleutel_nette_fout(tmp_path, vlpbek_bestand, monkeypatch, capsys):
    monkeypatch.delenv(SLEUTEL_ENV)
    monkeypatch.setattr(
        sys, "argv", ["ho", "verwerk", str(vlpbek_bestand), str(tmp_path)]
    )
    with pytest.raises(SystemExit) as uitkomst:
        main()
    assert uitkomst.value.code == 1
    assert SLEUTEL_ENV in capsys.readouterr().err


def test_cli_met_sleutelbestand(tmp_path, vlpbek_bestand, monkeypatch):
    monkeypatch.delenv(SLEUTEL_ENV)
    bestand = tmp_path / "sleutel.txt"
    bestand.write_text(TEST_SLEUTEL)
    doel = tmp_path / "prep"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ho",
            "verwerk",
            str(vlpbek_bestand),
            str(doel),
            "--sleutelbestand",
            str(bestand),
        ],
    )
    main()
    brd = pl.read_parquet(doel / "BRD.parquet")
    assert brd["Burgerservicenummer"][0] == REFERENTIE_1CIJFERHO["700010001"]


def test_bsn_wordt_gepseudonimiseerd_zoals_het_in_het_bestand_staat(tmp_path):
    """Geen normalisatie vooraf: voorloopnullen blijven, net als in 1cijferho."""
    regels = analyse_regels()
    regels = [r.replace("700010001", "012345678") for r in regels]
    pad = schrijf_bestand(tmp_path, "VLPBEK_2025_20240115_99XX.csv", regels)
    frames = run_pipeline(pad, tmp_path / "prep")
    assert frames["BRD"]["Burgerservicenummer"][0] == REFERENTIE_1CIJFERHO["012345678"]
