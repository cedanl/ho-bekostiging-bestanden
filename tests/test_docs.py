"""De documentatie in docs/ blijft gelijk aan de schema's en codelijsten.

Veld-, code- en tabeltabellen in de docs zijn met de hand bijgehouden. Deze
tests laten een schemawijziging zonder docs-wijziging falen, en vangen kapotte
verwijzingen die ``mkdocs build --strict`` alleen als INFO meldt.
"""

import csv
import re
import unicodedata
from pathlib import Path

import pytest

from ho_bekostiging_bestanden.metadata import SCHEMA_DIR, load_schema
from ho_bekostiging_bestanden.star import STAR_TABELLEN

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
# Planning en demo-materiaal horen niet bij de site (zie exclude_docs in mkdocs.yml).
UITGESLOTEN = ("superpowers", "demo", "assets")

# Recordtypepagina → (schema, recordsoort) in de volgorde waarin ze op de pagina staan.
RECORDPAGINAS = {
    "vlp": [("analyse", "VLP"), ("hisbek", "VLP")],
    "blb": [("analyse", "BLB")],
    "brd": [("analyse", "BRD")],
    "brr": [("analyse", "BRR")],
    "hrd": [("hisbek", "HRD")],
    "hrr": [("hisbek", "HRR")],
    "slr": [("analyse", "SLR"), ("hisbek", "SLR")],
}

_VELDRIJ = re.compile(r"^\| (\d+) \| `(\w+)` \|", re.MULTILINE)
_KOP = re.compile(r"^#{1,6} (.+?)\s*$", re.MULTILINE)
_LINK = re.compile(r"\]\(([^)\s]+\.md)?(#[^)\s]*)?\)")


def _tabellen(pagina: Path) -> list[list[str]]:
    """Veldnamen per tabel; een nieuwe tabel begint bij positie 1."""
    tabellen: list[list[str]] = []
    for pos, veld in _VELDRIJ.findall(pagina.read_text(encoding="utf-8")):
        if pos == "1":
            tabellen.append([])
        tabellen[-1].append(veld)
    return tabellen


def _slug(kop: str) -> str:
    """Anker van een kop, zoals Python-Markdown (de toc-extensie van MkDocs)."""
    tekst = unicodedata.normalize("NFKD", kop).encode("ascii", "ignore").decode()
    tekst = re.sub(r"[^\w\s-]", "", tekst).strip().lower()
    return re.sub(r"[-\s]+", "-", tekst)


def _ankers(pagina: Path) -> set[str]:
    return {_slug(k) for k in _KOP.findall(pagina.read_text(encoding="utf-8"))}


def _paginas() -> list[Path]:
    return sorted(
        p for p in DOCS.rglob("*.md") if p.relative_to(DOCS).parts[0] not in UITGESLOTEN
    )


@pytest.mark.parametrize("pagina", RECORDPAGINAS)
def test_recordtypepagina_heeft_alle_schemavelden_in_volgorde(pagina: str) -> None:
    verwacht = [
        load_schema(schema)[rs]["fields"] for schema, rs in RECORDPAGINAS[pagina]
    ]
    assert _tabellen(DOCS / "recordtypes" / f"{pagina}.md") == verwacht


def test_elke_recordsoort_heeft_een_pagina() -> None:
    in_schema = {
        rs.lower() for schema in ("analyse", "hisbek") for rs in load_schema(schema)
    }
    assert in_schema == set(RECORDPAGINAS)


def test_waardenlijsten_bevatten_elke_code() -> None:
    tekst = (DOCS / "waardenlijsten.md").read_text(encoding="utf-8")
    ontbreekt = []
    for pad in sorted(SCHEMA_DIR.glob("*.csv")):
        with pad.open(encoding="utf-8", newline="") as f:
            for rij in csv.DictReader(f):
                if f"| `{rij['Code']}` | {rij['Omschrijving']}" not in tekst:
                    ontbreekt.append(f"{pad.stem}:{rij['Code']}")
    assert not ontbreekt


@pytest.mark.parametrize("tabel", STAR_TABELLEN)
def test_datamodel_beschrijft_elke_startabel(tabel: str) -> None:
    tekst = (DOCS / "datamodel.md").read_text(encoding="utf-8")
    assert f"\n### {tabel}\n" in tekst


def test_nav_en_docs_komen_overeen() -> None:
    nav = (REPO / "mkdocs.yml").read_text(encoding="utf-8").split("\nnav:\n")[1]
    in_nav = set(re.findall(r"(\S+\.md)\s*$", nav, flags=re.MULTILINE))
    op_schijf = {p.relative_to(DOCS).as_posix() for p in _paginas()}
    assert in_nav == op_schijf


def test_interne_links_en_ankers_bestaan() -> None:
    kapot = []
    for pagina in _paginas():
        for doel, anker in _LINK.findall(pagina.read_text(encoding="utf-8")):
            if doel.startswith("http"):
                continue
            bestand = (pagina.parent / doel).resolve() if doel else pagina
            if not bestand.exists():
                kapot.append(f"{pagina.name}: {doel} bestaat niet")
            elif anker and anker[1:] not in _ankers(bestand):
                kapot.append(f"{pagina.name}: {doel}{anker} heeft geen kop")
    assert not kapot, "\n".join(kapot)
