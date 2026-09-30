"""Guard: tekstuele bestands-IO geeft altijd een encoding mee.

Zonder encoding gebruikt Python op Windows cp1252 (zie
cedanl/mbo-bekostiging-bestanden#383). Ruff PLW1514 ziet alleen aanroepen
waarvan het type bekend is, niet ``tmp_path / "x"``; deze guard wel.
"""

import ast
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).parents[1]
MAPPEN = ("src", "app", "scripts", "tests")
IO_AANROEPEN = {"open", "read_text", "write_text"}


def _naam(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _binaire_open(call: ast.Call) -> bool:
    modi = [a.value for a in call.args if isinstance(a, ast.Constant)]
    modi += [
        k.value.value
        for k in call.keywords
        if k.arg == "mode" and isinstance(k.value, ast.Constant)
    ]
    return any(isinstance(m, str) and "b" in m for m in modi)


def _zonder_encoding(pad: Path) -> Iterator[str]:
    boom = ast.parse(pad.read_text(encoding="utf-8"))
    for node in ast.walk(boom):
        if not isinstance(node, ast.Call):
            continue
        naam = _naam(node.func)
        if naam not in IO_AANROEPEN:
            continue
        if any(k.arg == "encoding" for k in node.keywords):
            continue
        if naam == "open" and _binaire_open(node):
            continue
        yield f"{pad.relative_to(ROOT).as_posix()}:{node.lineno}"


def test_tekstuele_io_heeft_encoding():
    bevindingen = [
        regel
        for map_ in MAPPEN
        for pad in sorted((ROOT / map_).rglob("*.py"))
        for regel in _zonder_encoding(pad)
    ]
    assert bevindingen == []
