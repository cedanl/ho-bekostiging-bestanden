import sys

from ho_bekostiging_bestanden.cli import main


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
