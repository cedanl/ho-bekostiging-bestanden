import sys

from ho_bekostiging_bestanden.cli import main


def test_cli_verwerk(tmp_path, vlpbek_bestand, monkeypatch, capsys):
    doel = tmp_path / "prep"
    monkeypatch.setattr(sys, "argv", ["ho", "verwerk", str(vlpbek_bestand), str(doel)])
    main()
    assert "Verwerkt:" in capsys.readouterr().out
    assert (doel / "BRD.parquet").exists()
