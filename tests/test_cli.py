import sys

from ho_bekostiging_bestanden.cli import main

from .conftest import analyse_regels, schrijf_bestand


def test_cli_verwerk(tmp_path, vlpbek_bestand, monkeypatch, capsys):
    doel = tmp_path / "prep"
    monkeypatch.setattr(sys, "argv", ["ho", "verwerk", str(vlpbek_bestand), str(doel)])
    main()
    assert "Verwerkt:" in capsys.readouterr().out
    assert (doel / "BRD.parquet").exists()


def test_cli_star(tmp_path, vlpbek_bestand, monkeypatch, capsys):
    prep = tmp_path / "prep" / vlpbek_bestand.stem
    monkeypatch.setattr(sys, "argv", ["ho", "verwerk", str(vlpbek_bestand), str(prep)])
    main()
    uit = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["ho", "star", str(prep), "--output", str(uit)])
    main()
    assert "Star schema gebouwd: 9 tabellen" in capsys.readouterr().out
    assert (uit / "datamodel" / "fact_deelname.parquet").exists()


def test_cli_werkt_op_windows_console(tmp_path, vlpbek_bestand, monkeypatch):
    """Een cp1252-console (standaard Windows) mag niet crashen op de uitvoer."""
    import io

    uit = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", uit)
    doel = tmp_path / "prep"
    monkeypatch.setattr(sys, "argv", ["ho", "verwerk", str(vlpbek_bestand), str(doel)])
    main()


def _fout_bestand(tmp_path):
    regels = analyse_regels()
    regels.insert(1, "XYZ|x")  # onbekende recordsoort → error
    return schrijf_bestand(tmp_path / "raw", "VLPBEK_2025_20240115_99XX.csv", regels)


def _draai(monkeypatch, *argv) -> int:
    monkeypatch.setattr(sys, "argv", ["ho", *map(str, argv)])
    try:
        main()
    except SystemExit as exit_:
        return int(exit_.code or 0)
    return 0


def test_cli_verwerk_fail_geeft_exitcode_3(tmp_path, monkeypatch, capsys):
    code = _draai(monkeypatch, "verwerk", _fout_bestand(tmp_path), tmp_path / "prep")
    assert code == 3
    assert "Kwaliteitsstatus fail" in capsys.readouterr().err
    assert (tmp_path / "prep" / "VALIDATIE.parquet").exists()


def test_cli_verwerk_fail_toegestaan(tmp_path, monkeypatch, capsys):
    bestand = _fout_bestand(tmp_path)
    code = _draai(
        monkeypatch, "verwerk", bestand, tmp_path / "prep", "--allow-quality-errors"
    )
    assert code == 0
    uit = capsys.readouterr().out
    assert "Let op: kwaliteitsstatus fail (1 error(s)), toegestaan." in uit


def test_cli_star_fail_en_toegestaan(tmp_path, monkeypatch, capsys):
    prep = tmp_path / "prep"
    bestand = _fout_bestand(tmp_path)
    _draai(monkeypatch, "verwerk", bestand, prep, "--allow-quality-errors")
    uit = tmp_path / "out"
    assert _draai(monkeypatch, "star", prep, "--output", uit) == 3
    capsys.readouterr()
    toegestaan = ["--allow-quality-errors"]
    assert _draai(monkeypatch, "star", prep, "--output", uit, *toegestaan) == 0
    assert "toegestaan" in capsys.readouterr().out


def test_cli_schoon_geen_let_op(tmp_path, vlpbek_bestand, monkeypatch, capsys):
    args = ["verwerk", vlpbek_bestand, tmp_path / "prep", "--allow-quality-errors"]
    assert _draai(monkeypatch, *args) == 0
    assert "Let op: kwaliteitsstatus" not in capsys.readouterr().out


def test_cli_alleen_warnings_exitcode_0(tmp_path, monkeypatch, capsys):
    # Jaar in de bestandsnaam wijkt af van de VLP → warning.
    bestand = schrijf_bestand(
        tmp_path / "raw", "VLPBEK_2024_20240115_99XX.csv", analyse_regels()
    )
    assert _draai(monkeypatch, "verwerk", bestand, tmp_path / "prep") == 0
    assert "Let op" not in capsys.readouterr().out


def test_cli_invoerfout_blijft_exitcode_1(tmp_path, monkeypatch):
    bestaat_niet = tmp_path / "VLPBEK_2025_20240115_99XX.csv"
    assert _draai(monkeypatch, "verwerk", bestaat_niet, tmp_path / "p") == 1


def test_cli_privacywaarschuwing_ook_bij_fail(tmp_path, monkeypatch, capsys):
    args = ["verwerk", _fout_bestand(tmp_path), tmp_path / "prep"]
    assert _draai(monkeypatch, *args, "--geen-pseudonimisering") == 3
    assert "NIET gepseudonimiseerd" in capsys.readouterr().err
