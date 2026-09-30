# Kwaliteitsbewaking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** HO krijgt het kwaliteitscontract van mbo-bekostiging-bestanden: ernst per melding, een kwaliteitspoort (exitcode 3), contracten op het star schema, `quality.json` met provenance, en Windows-robuuste bestands-IO.

**Architecture:** Een nieuwe module `kwaliteit.py` bevat het gedeelde contract (ernst, status, `KwaliteitsFout`, `poort`, `quality.json`). `validate.py` en de nieuwe module `contracten.py` leveren meldingen in één schema. `pipeline.py` voegt die samen, schrijft de uitvoer altijd weg en sluit daarna de poort. CLI en app lezen alleen status en meldingen.

**Tech Stack:** Python 3.13, Polars, Streamlit (AppTest), pytest, ruff, ty, uv; `jsonschema` (dev) voor T3.

**Spec:** `docs/superpowers/specs/2026-09-30-kwaliteitsbewaking-design.md` (pitch #18; tasks #19–#22)

## Global Constraints

- Namen gelijk aan MBO: `KwaliteitsFout`, `ERNST_ERROR = "error"`, `ERNST_WARNING = "warning"`, `STATUS_OK/WARN/FAIL = "ok"/"warn"/"fail"`, `EXIT_KWALITEIT = 3`, `fail_on_errors`, `--allow-quality-errors`, `lees_status`, `QUALITY_JSON = "quality.json"`.
- Exitcode 1 blijft voor invoerfouten (`ValueError`, `FileNotFoundError`); 3 is alleen voor kwaliteitsstatus `fail`.
- De uitvoer (prepared, `datamodel/`, `quality.json`) wordt **altijd** geschreven vóór een `KwaliteitsFout`.
- Geen hardcoded lijsten waar de schema-TOML's de bron zijn (recordsoorten voor de dekking).
- Alle tekst-IO met `encoding="utf-8"`; CLI-uitvoer blijft ASCII.
- Pseudonimisering (`pseudonimisering.py`) niet aanraken.
- `CLAUDE.md`: **geen commit tenzij de gebruiker erom vraagt**. De commit-stappen hieronder worden pas uitgevoerd na expliciet akkoord.
- Tests draaien met `uv run pytest`; de lint-gate is `uv run ruff check . && uv run ruff format --check . && uv run ty check`.

## Review Focus

- **Oude prepared-map** (van vóór T1, `VALIDATIE` zonder `Ernst`) naast een nieuwe: moet `fail` geven met "verwerk opnieuw", niet stil `ok`. Test in Task 2.
- **Lege ruwe map** (geen enkele levering): status `ok`, `quality.json` bestaat met lege lijsten, en er treedt geen exception op. Test in Task 2, en in Task 4 tegen het schema.
- **Alleen warnings** (jaar-mismatch, onbekende code): de CLI geeft exitcode 0 en geen "Let op"-regel; de status is `warn`. Test in Task 2 (pipeline én CLI).
- **Niet-ASCII in meldingen** ("Eén rij") via `quality.json` op een cp1252-machine: `lees_status` moet round-trippen. Test in Task 2.
- **Lege star-tabellen** (scenario alleen HISBEK, geen BRD/BRR): de contracten mogen niet crashen en de status is `ok`. Test in Task 3 via de scenario-tests (die in Task 2 `status == ok` gaan eisen).

---

### Task 1: Windows-robuustheid en CI (#22)

**Files:**
- Create: `tests/test_encoding.py`
- Modify: `pyproject.toml` (`[tool.ruff.lint]`)
- Modify: `.github/workflows/ci.yml`
- Modify (encoding erbij): `tests/test_app.py:23,68`, `tests/test_dashboard.py:24`, `tests/test_ingest.py:101`, `tests/test_pipeline.py:51`, `tests/test_pseudonimisering.py:45,94`, `tests/test_ruwe_randjes.py:73,81,93,105,112`, `tests/test_scenarios.py:53`, plus alles wat de guard verder vindt

**Interfaces:**
- Consumes: niets
- Produces: de guard `tests/test_encoding.py::test_tekstuele_io_heeft_encoding`; alle latere tasks moeten hem groen houden.

- [ ] **Step 1: Write the failing guard test**

`tests/test_encoding.py`:

```python
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
    modi += [k.value.value for k in call.keywords if k.arg == "mode"
             and isinstance(k.value, ast.Constant)]
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
```

- [ ] **Step 2: Run it to see it fail**

Run: `uv run pytest tests/test_encoding.py -v`
Expected: FAIL, de lijst bevat in ieder geval `tests/test_ingest.py:101`, `tests/test_pipeline.py:51`, `tests/test_ruwe_randjes.py:105` (positioneel `"utf-8"`) en `:112`.

- [ ] **Step 3: Fix every reported call**

Voeg `encoding="utf-8"` als keyword toe aan elke gemelde aanroep. Bijvoorbeeld:

```python
pad.write_text("\r\n\r\n", encoding="utf-8")                       # test_ingest.py:101
pad.write_text("VLP|x", encoding="utf-8")                          # test_pipeline.py:51
p.read_text(encoding="utf-8")                                      # test_ruwe_randjes.py:105 (was read_text("utf-8"))
tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))  # test_ruwe_randjes.py:112
```

Bij meerregelige `config.write_text(...)`-aanroepen (`test_app.py`, `test_dashboard.py`, `test_ruwe_randjes.py:93`) komt `encoding="utf-8",` als laatste argument. Wijzig geen gedrag: alleen het argument toevoegen. Meldt de guard een aanroep die geen bestands-IO is (bijv. `os.open`), sluit hem dan niet uit met een uitzondering zonder eerst te kijken; rapporteer het.

- [ ] **Step 4: Run the guard again**

Run: `uv run pytest tests/test_encoding.py -v`
Expected: PASS

- [ ] **Step 5: Enable PLW1514 in ruff**

`pyproject.toml`, sectie `[tool.ruff.lint]`:

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "PLW1514"]
# PLW1514 (unspecified-encoding) is een preview-regel; alleen die aanzetten.
preview = true
explicit-preview-rules = true
```

Run: `uv run ruff check .`
Expected: `All checks passed!`. Geeft `preview = true` nieuwe meldingen op bestaande regels, los die dan op als ze triviaal zijn (Boy Scout); anders rapporteren en stoppen.

- [ ] **Step 6: CI-matrix met Windows**

`.github/workflows/ci.yml` wordt:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Sync dependencies
        run: uv sync --group dev
      - name: Lint
        run: uv run ruff check .
      - name: Format
        run: uv run ruff format --check .
      - name: Type check
        run: uv run ty check

  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Sync dependencies
        run: uv sync --group dev
      - name: Test
        run: uv run pytest
```

- [ ] **Step 7: Full verification**

Run: `uv run pytest -q` en `uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: alles groen (157 + 1 tests).

- [ ] **Step 8: Commit (alleen na akkoord gebruiker)**

```bash
git add pyproject.toml .github/workflows/ci.yml tests/
git commit -m "fix(#22): utf-8 bij alle tekst-IO, ruff PLW1514 en windows-latest in CI"
```

---

### Task 2: Ernst en kwaliteitspoort (#19)

**Files:**
- Create: `src/ho_bekostiging_bestanden/kwaliteit.py`
- Create: `tests/test_kwaliteit.py`
- Modify: `src/ho_bekostiging_bestanden/validate.py`
- Modify: `src/ho_bekostiging_bestanden/pipeline.py`
- Modify: `src/ho_bekostiging_bestanden/cli.py`
- Modify: `app/pages/home.py:119-140`
- Modify tests: `tests/test_validate.py`, `tests/test_pipeline.py`, `tests/test_cli.py`, `tests/test_demo.py:29-33`, `tests/test_scenarios.py:45`, `tests/test_app.py`

**Interfaces:**
- Consumes: niets
- Produces (`kwaliteit.py`):
  - `ERNST_ERROR: str`, `ERNST_WARNING: str`, `ERNST_KOLOM = "Ernst"`, `BRON_KOLOM = "Bron"`
  - `STATUS_OK`, `STATUS_WARN`, `STATUS_FAIL: str`, `STAR_BRON = "star schema"`, `QUALITY_JSON = "quality.json"`
  - `MELDING_SCHEMA: dict[str, pl.DataType]` = Controle, Recordsoort, Melding (Utf8), Aantal (Int64), Ernst (Utf8)
  - `RAPPORT_SCHEMA` = `{"Bron": pl.Utf8, **MELDING_SCHEMA}`
  - `melding(controle: str, recordsoort: str, tekst: str, ernst: str, aantal: int = 1) -> dict`
  - `meldingen_frame(rijen: list[dict]) -> pl.DataFrame` (MELDING_SCHEMA)
  - `met_bron(meldingen: pl.DataFrame, bron: str) -> pl.DataFrame` (RAPPORT_SCHEMA)
  - `status(meldingen: pl.DataFrame) -> str`
  - `aantal(meldingen: pl.DataFrame, ernst: str) -> int` (aantal meldingen, niet de som van `Aantal`)
  - `class KwaliteitsFout(Exception)` met attribuut `meldingen: pl.DataFrame`
  - `poort(meldingen: pl.DataFrame, verwijzing: str) -> None`
  - `bouw_rapport(meldingen: pl.DataFrame, dim_levering: pl.DataFrame, fouten_toegestaan: bool) -> dict[str, Any]`
  - `schrijf_rapport(rapport: dict[str, Any], map_: Path) -> Path`
  - `lees_status(pad: Path | str) -> tuple[str, int]`
- Produces (`pipeline.py`): `run_pipeline(..., fail_on_errors: bool = True)`, `run_star(sources, target, fail_on_errors: bool = True)`, `Verwerking.status: str`, `Verwerking.meldingen: pl.DataFrame` (RAPPORT_SCHEMA); `Verwerking.validatie` vervalt. Intern: `_bouw_star(sources, target, fouten_toegestaan) -> tuple[dict[str, pl.DataFrame], pl.DataFrame]` en `_star_meldingen(star) -> pl.DataFrame` (in deze task leeg; Task 3 vult hem).
- Produces (`cli.py`): `EXIT_KWALITEIT = 3`.

- [ ] **Step 1: Failing tests for the contract**

`tests/test_kwaliteit.py`:

```python
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
```

Run: `uv run pytest tests/test_kwaliteit.py -v`
Expected: FAIL met `ModuleNotFoundError: ho_bekostiging_bestanden.kwaliteit`

- [ ] **Step 2: Implement `kwaliteit.py`**

```python
"""Gedeeld kwaliteitscontract: ernst, status, poort en ``quality.json``.

Namen zijn gelijk aan mbo-bekostiging-bestanden, zodat een gedeelde
kernbibliotheek (#9) later eenvoudig is. Een error zet de status op ``fail``;
de uitvoer wordt dan wel geschreven, maar ``poort`` gooit ``KwaliteitsFout``.
"""

import json
from pathlib import Path
from typing import Any

import polars as pl

from ho_bekostiging_bestanden.stack import LABEL_COL

ERNST_ERROR = "error"
ERNST_WARNING = "warning"
STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
QUALITY_JSON = "quality.json"
STAR_BRON = "star schema"
ERNST_KOLOM = "Ernst"
BRON_KOLOM = "Bron"

MELDING_SCHEMA = {
    "Controle": pl.Utf8,
    "Recordsoort": pl.Utf8,
    "Melding": pl.Utf8,
    "Aantal": pl.Int64,
    ERNST_KOLOM: pl.Utf8,
}
RAPPORT_SCHEMA = {BRON_KOLOM: pl.Utf8, **MELDING_SCHEMA}


class KwaliteitsFout(Exception):
    """De kwaliteitsstatus is ``fail``; de uitvoer staat al op schijf.

    ``meldingen`` bevat de error-meldingen (``RAPPORT_SCHEMA``).
    """

    def __init__(self, bericht: str, meldingen: pl.DataFrame) -> None:
        super().__init__(bericht)
        self.meldingen = meldingen


def melding(
    controle: str, recordsoort: str, tekst: str, ernst: str, aantal: int = 1
) -> dict:
    return {
        "Controle": controle,
        "Recordsoort": recordsoort,
        "Melding": tekst,
        "Aantal": aantal,
        ERNST_KOLOM: ernst,
    }


def meldingen_frame(rijen: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rijen, schema=MELDING_SCHEMA)


def met_bron(meldingen: pl.DataFrame, bron: str) -> pl.DataFrame:
    """Meldingen van één bron (levering of star schema) in ``RAPPORT_SCHEMA``."""
    return meldingen.select(pl.lit(bron).alias(BRON_KOLOM), *MELDING_SCHEMA)


def aantal(meldingen: pl.DataFrame, ernst: str) -> int:
    """Aantal meldingen met deze ernst (niet de som van ``Aantal``)."""
    return meldingen.filter(pl.col(ERNST_KOLOM) == ernst).height


def status(meldingen: pl.DataFrame) -> str:
    if aantal(meldingen, ERNST_ERROR):
        return STATUS_FAIL
    if aantal(meldingen, ERNST_WARNING):
        return STATUS_WARN
    return STATUS_OK


def poort(meldingen: pl.DataFrame, verwijzing: str) -> None:
    """Gooi :class:`KwaliteitsFout` als de status ``fail`` is."""
    if status(meldingen) != STATUS_FAIL:
        return
    fouten = meldingen.filter(pl.col(ERNST_KOLOM) == ERNST_ERROR)
    raise KwaliteitsFout(
        f"Kwaliteitsstatus {STATUS_FAIL}: {fouten.height} error(s); {verwijzing}.",
        fouten,
    )


def _als_lijst(meldingen: pl.DataFrame) -> list[dict[str, Any]]:
    return [
        {kolom.lower(): waarde for kolom, waarde in rij.items()}
        for rij in meldingen.select(*MELDING_SCHEMA).iter_rows(named=True)
    ]


def _onderdeel(meldingen: pl.DataFrame, bron: str) -> dict[str, Any]:
    eigen = meldingen.filter(pl.col(BRON_KOLOM) == bron)
    return {"status": status(eigen), "meldingen": _als_lijst(eigen)}


def bouw_rapport(
    meldingen: pl.DataFrame, dim_levering: pl.DataFrame, fouten_toegestaan: bool
) -> dict[str, Any]:
    """Inhoud van ``quality.json``: status, totalen, per levering en star.

    Args:
        meldingen:         Alle meldingen (``RAPPORT_SCHEMA``).
        dim_levering:      Levert de leveringslabels (kolom ``LABEL_COL``).
        fouten_toegestaan: Of de aanroeper een ``fail`` toestaat.
    """
    labels = dim_levering[LABEL_COL].to_list()
    # Een verouderde prepared-map kan meldingen hebben zonder rij in dim_levering.
    labels += sorted(
        set(meldingen[BRON_KOLOM].to_list()) - set(labels) - {STAR_BRON}
    )
    return {
        "status": status(meldingen),
        "fouten_toegestaan": fouten_toegestaan,
        "total_errors": aantal(meldingen, ERNST_ERROR),
        "total_warnings": aantal(meldingen, ERNST_WARNING),
        "leveringen": [
            {"levering": label, **_onderdeel(meldingen, label)} for label in labels
        ],
        "star": _onderdeel(meldingen, STAR_BRON),
    }


def schrijf_rapport(rapport: dict[str, Any], map_: Path) -> Path:
    """Schrijf ``quality.json`` (UTF-8) in ``map_`` en geef het pad terug."""
    map_.mkdir(parents=True, exist_ok=True)
    pad = map_ / QUALITY_JSON
    pad.write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return pad


def lees_status(pad: Path | str) -> tuple[str, int]:
    """``(status, aantal errors)`` uit een geschreven ``quality.json``."""
    rapport = json.loads(Path(pad).read_text(encoding="utf-8"))
    return rapport["status"], rapport["total_errors"]
```

Run: `uv run pytest tests/test_kwaliteit.py -v`
Expected: PASS (4 tests). De schema's volgen dezelfde vorm als de huidige `VALIDATIE_SCHEMA` (dtype-klassen zonder haakjes), zodat `pl.DataFrame(schema=...)` en ty zich hetzelfde gedragen als nu.

- [ ] **Step 3: Failing tests for ernst in `validate.py`**

In `tests/test_validate.py`:
- Import `from ho_bekostiging_bestanden.kwaliteit import ERNST_ERROR, ERNST_WARNING, MELDING_SCHEMA` en vervang `VALIDATIE_SCHEMA` door `MELDING_SCHEMA` (import en regel 26).
- Vervang `test_brin_in_naam_wijkt_af` en voeg toe:

```python
def test_brin_in_naam_wijkt_af_is_error(tmp_path):
    rapport = _valideer(
        tmp_path, analyse_regels(), naam="VLPBEK_2025_20240115_00AA.csv"
    )
    assert rapport["Controle"].to_list() == ["BRIN"]
    assert rapport["Ernst"].to_list() == [ERNST_ERROR]
    assert "00AA" in rapport["Melding"][0]


def test_jaar_in_naam_wijkt_af_is_warning(tmp_path):
    rapport = _valideer(
        tmp_path, analyse_regels(), naam="VLPBEK_2024_20240115_99XX.csv"
    )
    assert rapport["Controle"].to_list() == ["Bekostigingsjaar"]
    assert rapport["Ernst"].to_list() == [ERNST_WARNING]


def test_onbekende_code_is_warning(tmp_path):
    rapport = _valideer(tmp_path, analyse_regels(statussen=("pi", "zz", "mv")))
    assert rapport["Ernst"].to_list() == [ERNST_WARNING]


@pytest.mark.parametrize(
    "wijziging",
    ["onbekende_recordsoort", "extra_veld", "slr", "verplicht"],
)
def test_structurele_afwijking_is_error(tmp_path, wijziging):
    regels = analyse_regels()
    if wijziging == "onbekende_recordsoort":
        regels.insert(1, "XYZ|x")
    elif wijziging == "extra_veld":
        regels[2] = regels[2] + "|" * 30 + "EXTRA"
    elif wijziging == "slr":
        regels[-1] = regels[-1].replace("|3|", "|4|", 1)
    else:
        regels[2] = regels[2].replace("|34001|", "||", 1)
    rapport = _valideer(tmp_path, regels)
    assert ERNST_ERROR in rapport["Ernst"].to_list(), rapport.to_dicts()
```

Controleer vóór het draaien dat `regels[-1].replace("|3|", "|4|", 1)` in de SLR echt `AantalBRDrecords` raakt: `maak_regel("analyse", "SLR", …)` zet de velden in schemavolgorde. Raakt het een ander veld, gebruik dan dezelfde `maak_regel`-constructie als `test_slr_telling_klopt_niet`. Controleer ook of `regels[2] + "|" * 30 + "EXTRA"` voorbij het schema valt; `schrijf_bestand` vult op tot `PAD_TOT` velden, dus het extra veld moet voorbij `len(schema["BLB"]["fields"])` liggen.

Run: `uv run pytest tests/test_validate.py -v`
Expected: FAIL (`MELDING_SCHEMA` heeft `Ernst`, `valideer` nog niet; de controle heet nog `Bestandsnaam`)

- [ ] **Step 4: Implement ernst in `validate.py`**

Vervang de module-docstring, `VALIDATIE_SCHEMA` en `_melding`, en splits `_bestandsnaam`:

```python
"""Kwaliteitscontroles op een ingelezen levering.

Elke melding heeft een ernst (``ERNST_PER_CONTROLE``). Een error zet de
levering op ``fail``; de pipeline schrijft de uitvoer dan wel weg, maar sluit
daarna de kwaliteitspoort (zie ``kwaliteit.poort``). Alleen een ontbrekend
voorlooprecord is direct fataal, omdat de levering dan niet te plaatsen is.
"""

import re

import polars as pl

from ho_bekostiging_bestanden.decode import STATUS_SCHEIDING
from ho_bekostiging_bestanden.ingest import MELDINGEN, Bestandsinfo
from ho_bekostiging_bestanden.kwaliteit import (
    ERNST_ERROR,
    ERNST_WARNING,
    melding,
    meldingen_frame,
)
from ho_bekostiging_bestanden.metadata import load_codelijst, load_schema

VOORLOOP = "VLP"
SLUIT = "SLR"
_SLR_VELD_RE = re.compile(r"^Aantal([A-Z]{3})records$")

# Ernst per controle. Een onbekende code is een warning: dim_status vangt die
# op als "Onbekende code". Een ander jaar in de bestandsnaam is een warning,
# want de VLP is leidend; een andere BRIN is een error (verkeerde instelling).
ERNST_PER_CONTROLE = {
    "Inlezen": ERNST_ERROR,
    "Aantal records": ERNST_ERROR,
    "Eén rij": ERNST_ERROR,
    "Verplicht veld": ERNST_ERROR,
    "BRIN": ERNST_ERROR,
    "Bekostigingsjaar": ERNST_WARNING,
    "Codelijst": ERNST_WARNING,
}


def _melding(controle: str, rs: str, tekst: str, aantal: int = 1) -> dict:
    return melding(controle, rs, tekst, ERNST_PER_CONTROLE[controle], aantal)
```

In `_bestandsnaam`: `_melding("Bestandsnaam", VOORLOOP, f"BRIN in bestandsnaam …")` wordt `_melding("BRIN", VOORLOOP, …)`, en de jaar-melding wordt `_melding("Bekostigingsjaar", VOORLOOP, …)`. De teksten blijven gelijk.

In `valideer`: `return pl.DataFrame(rijen, schema=VALIDATIE_SCHEMA)` wordt `return meldingen_frame(rijen)`, en in de docstring wordt `VALIDATIE_SCHEMA` → `MELDING_SCHEMA (kwaliteit.py)`. Zoek met `grep -rn VALIDATIE_SCHEMA src app tests` naar overige gebruikers en zet ze om naar `MELDING_SCHEMA`.

Run: `uv run pytest tests/test_validate.py -v`
Expected: PASS

- [ ] **Step 5: Failing tests for the gate in `pipeline.py`**

Voeg toe aan `tests/test_pipeline.py` (imports erbij: `json`, `KwaliteitsFout`, `QUALITY_JSON`, `STATUS_FAIL`, `STATUS_OK`, `STATUS_WARN` uit `kwaliteit`, `run_star`, `verwerk_alles` uit `pipeline`, `analyse_regels`, `schrijf_bestand` uit `.conftest`):

```python
def _fout_bestand(map_):
    regels = analyse_regels()
    regels.insert(1, "XYZ|x")  # onbekende recordsoort → error
    return schrijf_bestand(map_, "VLPBEK_2025_20240115_99XX.csv", regels)


def test_run_pipeline_poort_na_wegschrijven(tmp_path):
    doel = tmp_path / "prep"
    with pytest.raises(KwaliteitsFout, match="1 error"):
        run_pipeline(_fout_bestand(tmp_path / "raw"), doel)
    validatie = pl.read_parquet(doel / f"{VALIDATIE}.parquet")
    assert validatie["Ernst"].to_list() == ["error"]


def test_run_pipeline_fouten_toegestaan(tmp_path):
    frames = run_pipeline(
        _fout_bestand(tmp_path / "raw"), tmp_path / "prep", fail_on_errors=False
    )
    assert frames[VALIDATIE].height == 1


def test_run_star_schrijft_quality_json_en_gooit(tmp_path):
    prep = tmp_path / "prep" / "lev"
    run_pipeline(_fout_bestand(tmp_path / "raw"), prep, fail_on_errors=False)
    uit = tmp_path / "out"
    with pytest.raises(KwaliteitsFout):
        run_star([prep], uit)
    assert (uit / "datamodel" / "fact_deelname.parquet").exists()
    rapport = json.loads((uit / QUALITY_JSON).read_text(encoding="utf-8"))
    assert rapport["status"] == STATUS_FAIL
    assert rapport["fouten_toegestaan"] is False
    assert rapport["leveringen"][0]["levering"] == "lev"


def test_verouderde_prepared_map_is_fail(tmp_path, vlpbek_bestand):
    prep = tmp_path / "prep" / "oud"
    run_pipeline(vlpbek_bestand, prep)
    pad = prep / f"{VALIDATIE}.parquet"
    pl.read_parquet(pad).drop("Ernst").write_parquet(pad)
    run_star([prep], tmp_path / "out", fail_on_errors=False)
    rapport = json.loads((tmp_path / "out" / QUALITY_JSON).read_text(encoding="utf-8"))
    assert rapport["status"] == STATUS_FAIL
    assert "verwerk" in rapport["leveringen"][0]["meldingen"][0]["melding"]


def test_verwerk_alles_gooit_niet_maar_meldt(tmp_path):
    raw = tmp_path / "raw"
    _fout_bestand(raw)
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.status == STATUS_FAIL
    assert resultaat.meldingen["Bron"].to_list() == ["VLPBEK_2025_20240115_99XX"]


def test_verwerk_alles_lege_map_is_ok(tmp_path):
    (tmp_path / "raw").mkdir()
    resultaat = verwerk_alles(tmp_path / "raw", tmp_path / "prep", tmp_path / "out")
    assert resultaat.status == STATUS_OK
    rapport = json.loads((tmp_path / "out" / QUALITY_JSON).read_text(encoding="utf-8"))
    assert rapport["leveringen"] == []


def test_alleen_warnings_is_warn(tmp_path):
    raw = tmp_path / "raw"
    schrijf_bestand(raw, "VLPBEK_2024_20240115_99XX.csv", analyse_regels())  # jaar wijkt af
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.status == STATUS_WARN
```

Pas ook aan:
- `tests/test_demo.py:29-33`:
  ```python
  def test_demo_verwerkt_zonder_fouten_of_meldingen(tmp_path):
      resultaat = verwerk_alles(DEMO_RAW, tmp_path / "prep", tmp_path / "out")
      assert resultaat.fouten == {}
      assert resultaat.status == STATUS_OK
      assert resultaat.meldingen.is_empty(), resultaat.meldingen.to_dicts()
  ```
- `tests/test_scenarios.py:45`: `assert resultaat.status == STATUS_OK` en `assert resultaat.meldingen.is_empty()` in plaats van de `validatie`-regel (import `STATUS_OK`).

Run: `uv run pytest tests/test_pipeline.py tests/test_demo.py tests/test_scenarios.py -v`
Expected: FAIL (`fail_on_errors` bestaat niet, `Verwerking` heeft geen `status`)

- [ ] **Step 6: Implement the gate in `pipeline.py`**

Imports erbij:

```python
from ho_bekostiging_bestanden.kwaliteit import (
    ERNST_ERROR,
    ERNST_KOLOM,
    QUALITY_JSON,
    RAPPORT_SCHEMA,
    STATUS_OK,
    bouw_rapport,
    melding,
    meldingen_frame,
    met_bron,
    poort,
    schrijf_rapport,
    status,
)
from ho_bekostiging_bestanden.stack import LABEL_COL, stack_prepared
```

Constante bovenaan (naast `DUBBEL_MELDING`):

```python
VEROUDERD_MELDING = (
    "Prepared-map zonder ernst per melding (van vóór de kwaliteitspoort); "
    "verwerk het bestand opnieuw."
)
```

`run_pipeline` krijgt `fail_on_errors: bool = True` (docstring: "Werp :class:`KwaliteitsFout` na het wegschrijven als de levering status ``fail`` heeft."; `Raises` aanvullen). Na `export_frames(...)`:

```python
    if fail_on_errors:
        poort(
            met_bron(rapport, Path(source).stem),
            f"zie de tabel {VALIDATIE} in {target}",
        )
    return uitvoer
```

Nieuwe helpers en `run_star`:

```python
def _leveringmeldingen(
    sources: Sequence[Path | str], stacked: dict[str, pl.DataFrame]
) -> pl.DataFrame:
    """Validatiemeldingen per levering, plus een error per verouderde map."""
    delen = [pl.DataFrame(schema=RAPPORT_SCHEMA)]
    validatie = stacked.get(VALIDATIE)
    if validatie is not None and ERNST_KOLOM in validatie.columns:
        # Rijen zonder ernst komen uit een verouderde map; die krijgt hieronder
        # één eigen error.
        delen.append(
            validatie.filter(pl.col(ERNST_KOLOM).is_not_null()).select(
                pl.col(LABEL_COL).alias(BRON_KOLOM), *MELDING_SCHEMA
            )
        )
    for map_ in map(Path, sources):
        pad = map_ / f"{VALIDATIE}.parquet"
        if not pad.exists() or ERNST_KOLOM not in pl.read_parquet_schema(pad):
            verouderd = melding(
                "Prepared-map", VALIDATIE, VEROUDERD_MELDING, ERNST_ERROR
            )
            delen.append(met_bron(meldingen_frame([verouderd]), map_.name))
    return pl.concat(delen)


def _star_meldingen(star: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Meldingen over het star schema zelf; Task 3 (#20) vult dit."""
    return pl.DataFrame(schema=RAPPORT_SCHEMA)


def _bouw_star(
    sources: Sequence[Path | str], target: str | Path, fouten_toegestaan: bool
) -> tuple[dict[str, pl.DataFrame], pl.DataFrame]:
    """Bouw en schrijf star schema en ``quality.json``; geef star en meldingen."""
    stacked = stack_prepared(sources)
    star = build_star(stacked)
    meldingen = pl.concat(
        [_leveringmeldingen(sources, stacked), _star_meldingen(star)]
    )
    export_frames(star, Path(target) / DATAMODEL_MAP)
    schrijf_rapport(
        bouw_rapport(meldingen, star["dim_levering"], fouten_toegestaan), Path(target)
    )
    return star, meldingen


def run_star(
    sources: Sequence[Path | str],
    target: str | Path,
    fail_on_errors: bool = True,
) -> dict[str, pl.DataFrame]:
    """Stapel prepared-mappen, bouw het star schema en schrijf het weg.

    Args:
        sources: Mappen met prepared Parquet-bestanden (één per levering).
        target:  Doelmap; het star schema komt in ``<target>/datamodel/`` en
                 het kwaliteitsrapport in ``<target>/quality.json``.
        fail_on_errors: Werp :class:`KwaliteitsFout` bij status ``fail``.

    Returns:
        Dict met de star-schema-tabellen.

    Raises:
        KwaliteitsFout: Bij status ``fail`` en ``fail_on_errors``; star schema en
                        ``quality.json`` staan dan al op schijf.
    """
    star, meldingen = _bouw_star(sources, target, not fail_on_errors)
    if fail_on_errors:
        poort(meldingen, f"zie {Path(target) / QUALITY_JSON}")
    return star
```

Voeg `BRON_KOLOM` en `MELDING_SCHEMA` toe aan de `kwaliteit`-import hierboven.

`Verwerking`:

```python
@dataclass
class Verwerking:
    """Uitkomst van :func:`verwerk_alles`."""

    prepared_dirs: list[Path] = field(default_factory=list)
    star: dict[str, pl.DataFrame] = field(default_factory=dict)
    fouten: dict[str, str] = field(default_factory=dict)
    status: str = STATUS_OK
    meldingen: pl.DataFrame = field(
        default_factory=lambda: pl.DataFrame(schema=RAPPORT_SCHEMA)
    )
```

In `verwerk_alles`:
- `run_pipeline(bestand, doel, sleutel=..., pseudonimiseer=..., fail_on_errors=False)`
- De regel `resultaat.validatie[bestand.name] = frames[VALIDATIE]` vervalt (en `frames =` wordt dan overbodig).
- Het einde wordt:

```python
    resultaat.star, resultaat.meldingen = _bouw_star(
        resultaat.prepared_dirs, output, fouten_toegestaan=False
    )
    resultaat.status = status(resultaat.meldingen)
    return resultaat
```

- De docstring noemt: "Gooit geen :class:`KwaliteitsFout`; ``status`` en ``meldingen`` geven de kwaliteit."

Run: `uv run pytest tests/test_pipeline.py tests/test_demo.py tests/test_scenarios.py -v`
Expected: PASS

- [ ] **Step 7: Failing tests for the CLI**

In `tests/test_cli.py` (imports: `pytest`, `from .conftest import analyse_regels, schrijf_bestand`):

```python
def _fout_bestand(tmp_path):
    regels = analyse_regels()
    regels.insert(1, "XYZ|x")
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
    code = _draai(
        monkeypatch, "verwerk", _fout_bestand(tmp_path), tmp_path / "prep",
        "--allow-quality-errors",
    )
    assert code == 0
    assert "Let op: kwaliteitsstatus fail (1 error(s)), toegestaan." in capsys.readouterr().out


def test_cli_star_fail_en_toegestaan(tmp_path, monkeypatch, capsys):
    prep = tmp_path / "prep"
    _draai(monkeypatch, "verwerk", _fout_bestand(tmp_path), prep, "--allow-quality-errors")
    assert _draai(monkeypatch, "star", prep, "--output", tmp_path / "out") == 3
    assert _draai(
        monkeypatch, "star", prep, "--output", tmp_path / "out", "--allow-quality-errors"
    ) == 0
    assert "toegestaan" in capsys.readouterr().out


def test_cli_schoon_geen_let_op(tmp_path, vlpbek_bestand, monkeypatch, capsys):
    assert _draai(monkeypatch, "verwerk", vlpbek_bestand, tmp_path / "prep",
                  "--allow-quality-errors") == 0
    assert "Let op: kwaliteitsstatus" not in capsys.readouterr().out


def test_cli_alleen_warnings_exitcode_0(tmp_path, monkeypatch, capsys):
    bestand = schrijf_bestand(
        tmp_path / "raw", "VLPBEK_2024_20240115_99XX.csv", analyse_regels()
    )  # jaar in de naam wijkt af van de VLP → warning
    assert _draai(monkeypatch, "verwerk", bestand, tmp_path / "prep") == 0
    assert "Let op" not in capsys.readouterr().out


def test_cli_invoerfout_blijft_exitcode_1(tmp_path, monkeypatch):
    assert _draai(monkeypatch, "verwerk", tmp_path / "bestaat_niet.csv", tmp_path / "p") == 1
```

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL (`unrecognized arguments: --allow-quality-errors`, en exitcode 3 ontbreekt)

- [ ] **Step 8: Implement the CLI**

`cli.py`:
- Module-docstring: voeg `[--allow-quality-errors]` toe aan beide gebruiksregels, plus de zin "Exitcode 1 bij een invoerfout, 3 bij kwaliteitsstatus fail."
- Imports:

```python
from ho_bekostiging_bestanden.ingest import VALIDATIE
from ho_bekostiging_bestanden.kwaliteit import (
    ERNST_ERROR,
    QUALITY_JSON,
    STATUS_FAIL,
    KwaliteitsFout,
    aantal,
    lees_status,
    status,
)
```

- Constanten en helper:

```python
# Exitcode bij kwaliteitsstatus fail, gelijk aan mbo-bekostiging-bestanden (#361).
EXIT_KWALITEIT = 3


def _meld_toegestaan(stat: str, fouten: int) -> None:
    if stat == STATUS_FAIL:
        print(f"Let op: kwaliteitsstatus {stat} ({fouten} error(s)), toegestaan.")
```

- In `_verwerk`: geef `fail_on_errors=not args.allow_quality_errors` door aan `run_pipeline`. Na de "Verwerkt:"-print:

```python
    validatie = frames[VALIDATIE]
    _meld_toegestaan(status(validatie), aantal(validatie, ERNST_ERROR))
```

- In `_star`: `run_star(args.sources, args.output, fail_on_errors=not args.allow_quality_errors)`. Na de print: `_meld_toegestaan(*lees_status(args.output / QUALITY_JSON))`.
- Helper, en in `build_parser` aanroepen met `_voeg_kwaliteitsoptie_toe(p_verwerk)` en `_voeg_kwaliteitsoptie_toe(p_star)` vóór de bijbehorende `set_defaults`:

```python
def _voeg_kwaliteitsoptie_toe(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-quality-errors",
        action="store_true",
        dest="allow_quality_errors",
        help="Exitcode 0 ook bij kwaliteitsstatus fail (uitvoer wordt altijd geschreven)",
    )
```

- In `main`:

```python
    except KwaliteitsFout as fout:
        print(f"Fout: {fout}", file=sys.stderr)
        sys.exit(EXIT_KWALITEIT)
```

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS (ook de bestaande cp1252-test)

- [ ] **Step 9: Failing AppTest for Home**

In `tests/test_app.py`:

```python
def test_home_toont_errors_bij_fail(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    regels = analyse_regels()
    regels.insert(1, "XYZ|x")
    schrijf_bestand(raw, "VLPBEK_2025_20240115_99XX.csv", regels)
    config = tmp_path / "config.toml"
    config.write_text(
        "[data]\n"
        f'raw = "{raw.as_posix()}"\n'
        f'prepared = "{(tmp_path / "prep").as_posix()}"\n'
        f'output = "{(tmp_path / "out").as_posix()}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(CONFIG_ENV, str(config))
    at = _pagina("home").run()
    at.button(key="verwerk_alles").click().run()
    assert not at.exception
    assert any("Kwaliteitsstatus fail" in e.value for e in at.error)
    assert not at.success
```

(Import `analyse_regels`, `schrijf_bestand` uit `.conftest`.)

Run: `uv run pytest tests/test_app.py -v`
Expected: FAIL (Home gebruikt `resultaat.validatie`, en die bestaat niet meer)

- [ ] **Step 10: Implement Home**

In `app/pages/home.py` vervang je het blok na `st.spinner` (regels 127–140) door:

```python
    for naam, fout in resultaat.fouten.items():
        st.error(f"**{naam}** kon niet worden verwerkt: {fout}")
    meldingen = resultaat.meldingen
    fouten = meldingen.filter(pl.col(ERNST_KOLOM) == ERNST_ERROR)
    waarschuwingen = meldingen.filter(pl.col(ERNST_KOLOM) == ERNST_WARNING)
    if resultaat.status == STATUS_FAIL:
        st.error(
            f"Kwaliteitsstatus fail: {fouten.height} error(s). Het star schema is "
            "geschreven, maar de cijfers zijn niet betrouwbaar. Los de errors "
            "hieronder op en verwerk opnieuw."
        )
        st.dataframe(fouten.drop(ERNST_KOLOM), hide_index=True, width="stretch")
    if not waarschuwingen.is_empty():
        with st.expander(f"{waarschuwingen.height} waarschuwing(en)"):
            st.dataframe(
                waarschuwingen.drop(ERNST_KOLOM), hide_index=True, width="stretch"
            )
    if resultaat.status != STATUS_FAIL:
        totaal = sum(df.height for df in resultaat.star.values())
        st.success(
            f"{len(resultaat.prepared_dirs)} bestand(en) verwerkt; star schema met "
            f"{len(resultaat.star)} tabellen en {totaal:,} rijen."
        )
```

Imports in `home.py`: `polars as pl` (als die er nog niet is) en `from ho_bekostiging_bestanden.kwaliteit import ERNST_ERROR, ERNST_KOLOM, ERNST_WARNING, STATUS_FAIL`.

Run: `uv run pytest tests/test_app.py -v`
Expected: PASS

- [ ] **Step 11: Full verification**

Run: `uv run pytest -q` en `uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: alles groen.

- [ ] **Step 12: Commit (alleen na akkoord gebruiker)**

```bash
git add src/ho_bekostiging_bestanden/kwaliteit.py src/ho_bekostiging_bestanden/validate.py \
  src/ho_bekostiging_bestanden/pipeline.py src/ho_bekostiging_bestanden/cli.py \
  app/pages/home.py tests/
git commit -m "feat(#19): ernst per melding en kwaliteitspoort met exitcode 3"
```

---

### Task 3: Register met star-contracten (#20)

**Files:**
- Create: `src/ho_bekostiging_bestanden/contracten.py`
- Create: `tests/test_contracten.py`
- Modify: `src/ho_bekostiging_bestanden/pipeline.py` (`_star_meldingen`)

**Interfaces:**
- Consumes: `ERNST_ERROR`, `STAR_BRON`, `melding`, `meldingen_frame`, `met_bron` (Task 2); `FEIT_ID`, `PERSOON_ID` uit `star.py`; `LABEL_COL` uit `stack.py`.
- Produces: `GRAIN: dict[str, list[str]]`, `KOPPELINGEN: tuple[Koppeling, ...]`, `CONTROLES: tuple[Controle, ...]`, `controleer_star(star: dict[str, pl.DataFrame]) -> pl.DataFrame` (MELDING_SCHEMA).

- [ ] **Step 1: Failing tests**

`tests/test_contracten.py`:

```python
import polars as pl

from ho_bekostiging_bestanden.contracten import GRAIN, KOPPELINGEN, controleer_star
from ho_bekostiging_bestanden.kwaliteit import ERNST_ERROR, MELDING_SCHEMA
from ho_bekostiging_bestanden.star import STAR_TABELLEN


def test_register_dekt_alle_tabellen():
    assert set(GRAIN) == set(STAR_TABELLEN)
    for k in KOPPELINGEN:
        assert k.feit in STAR_TABELLEN and set(k.doelen) <= set(STAR_TABELLEN)


def test_demo_voldoet_aan_alle_contracten(demo_star):
    meldingen = controleer_star(demo_star)
    assert meldingen.schema == MELDING_SCHEMA
    assert meldingen.is_empty(), meldingen.to_dicts()


def test_een_dubbeling_een_lege_sleutel_een_wees(demo_star):
    star = dict(demo_star)
    opl = star["dim_opleiding"]
    star["dim_opleiding"] = pl.concat([opl, opl.head(1)])
    res = star["fact_resultaat"]
    star["fact_resultaat"] = res.with_columns(
        pl.when(pl.int_range(pl.len()) == 0).then(None).otherwise(pl.col("BRIN")).alias("BRIN")
    )
    st = star["fact_status"]
    star["fact_status"] = pl.concat(
        [st, st.head(1).with_columns(pl.lit("zz").alias("Code"))]
    )
    meldingen = controleer_star(star)
    assert sorted(meldingen["Controle"].to_list()) == ["Koppeling", "Lege sleutel", "Uniciteit"]
    assert set(meldingen["Recordsoort"]) == {"dim_opleiding", "fact_resultaat", "fact_status"}
    assert set(meldingen["Ernst"]) == {ERNST_ERROR}
```

Run: `uv run pytest tests/test_contracten.py -v`
Expected: FAIL met `ModuleNotFoundError: ho_bekostiging_bestanden.contracten`

- [ ] **Step 2: Implement `contracten.py`**

```python
"""Contracten op het star schema: uniciteit per grain, lege sleutels, koppelingen.

Los van de bouw in ``star.py`` (zoals ``contracts.py`` in
mbo-bekostiging-bestanden). Grain en koppelingen zijn declaratief; een nieuwe
star-tabel voeg je hier toe, niet in een if-keten.

Publieke API:
    controleer_star(star) -> pl.DataFrame  (MELDING_SCHEMA)
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import polars as pl

from ho_bekostiging_bestanden.kwaliteit import ERNST_ERROR, melding, meldingen_frame
from ho_bekostiging_bestanden.stack import LABEL_COL
from ho_bekostiging_bestanden.star import FEIT_ID, PERSOON_ID

Star = dict[str, pl.DataFrame]
# (recordsoort/tabel, meldingstekst, aantal)
Bevinding = tuple[str, str, int]

GRAIN: dict[str, list[str]] = {
    "dim_levering": [LABEL_COL],
    "dim_persoon": [PERSOON_ID],
    "dim_instelling": ["BRIN"],
    "dim_opleiding": ["Opleidingscode"],
    "dim_status": ["Code"],
    "fact_deelname": [FEIT_ID],
    "fact_resultaat": [FEIT_ID],
    "fact_status": [FEIT_ID, "Code"],
    "fact_loopbaan": [LABEL_COL, PERSOON_ID],
}


@dataclass(frozen=True)
class Koppeling:
    """Elke niet-lege ``kolom`` in ``feit`` bestaat in dezelfde kolom van een doel."""

    feit: str
    kolom: str
    doelen: tuple[str, ...]


_DEELNAME_RESULTAAT = ("fact_deelname", "fact_resultaat")
_FEITEN = (*_DEELNAME_RESULTAAT, "fact_status", "fact_loopbaan")

KOPPELINGEN: tuple[Koppeling, ...] = (
    *(Koppeling(f, LABEL_COL, ("dim_levering",)) for f in _FEITEN),
    *(
        Koppeling(f, PERSOON_ID, ("dim_persoon",))
        for f in (*_DEELNAME_RESULTAAT, "fact_loopbaan")
    ),
    *(Koppeling(f, "BRIN", ("dim_instelling",)) for f in _DEELNAME_RESULTAAT),
    *(Koppeling(f, "Opleidingscode", ("dim_opleiding",)) for f in _DEELNAME_RESULTAAT),
    Koppeling("fact_status", "Code", ("dim_status",)),
    Koppeling("fact_status", FEIT_ID, _DEELNAME_RESULTAAT),
)


def _dubbel(star: Star) -> Iterator[Bevinding]:
    for tabel, sleutel in GRAIN.items():
        n = int(star[tabel].select(sleutel).is_duplicated().sum())
        if n:
            yield tabel, f"{n} rijen met een dubbele sleutel ({', '.join(sleutel)})", n


def _sleutelkolommen(tabel: str) -> list[str]:
    koppel = [k.kolom for k in KOPPELINGEN if k.feit == tabel]
    return list(dict.fromkeys([*GRAIN[tabel], *koppel]))


def _leeg(star: Star) -> Iterator[Bevinding]:
    for tabel in GRAIN:
        for kolom in _sleutelkolommen(tabel):
            n = star[tabel][kolom].null_count()
            if n:
                yield tabel, f"{kolom} is leeg", n


def _wees(star: Star) -> Iterator[Bevinding]:
    for k in KOPPELINGEN:
        bekend = pl.concat([star[d][k.kolom] for d in k.doelen]).implode()
        kolom = pl.col(k.kolom)
        n = star[k.feit].filter(kolom.is_not_null() & ~kolom.is_in(bekend)).height
        if n:
            doelen = " / ".join(k.doelen)
            yield k.feit, f"{n} waarden van {k.kolom} ontbreken in {doelen}", n


@dataclass(frozen=True)
class Controle:
    naam: str
    ernst: str
    functie: Callable[[Star], Iterator[Bevinding]]


CONTROLES: tuple[Controle, ...] = (
    Controle("Uniciteit", ERNST_ERROR, _dubbel),
    Controle("Lege sleutel", ERNST_ERROR, _leeg),
    Controle("Koppeling", ERNST_ERROR, _wees),
)


def controleer_star(star: Star) -> pl.DataFrame:
    """Loop het register door; één melding per bevinding (``MELDING_SCHEMA``)."""
    return meldingen_frame(
        [
            melding(c.naam, tabel, tekst, c.ernst, n)
            for c in CONTROLES
            for tabel, tekst, n in c.functie(star)
        ]
    )
```

Let op de dtypes bij `_wees`: `Code` in `fact_status` en `dim_status` zijn allebei Utf8, en `_feit_id` ook. Geeft `pl.concat` van twee `_feit_id`-kolommen een fout, controleer dan de dtypes met `demo_star["fact_deelname"].schema`.

Run: `uv run pytest tests/test_contracten.py -v`
Expected: PASS (3 tests). Faalt de demo-test, controleer dan eerst of de demo echt een contract schendt (eerder op 30-09 nagegaan: 0 dubbelingen, 0 nulls, 0 wezen). Pas het contract niet aan om de test groen te krijgen zonder dat te melden.

- [ ] **Step 3: Failing integration test**

Voeg toe aan `tests/test_pipeline.py`:

```python
def test_star_contractbreuk_is_fail(tmp_path, vlpbek_bestand, monkeypatch):
    from ho_bekostiging_bestanden import contracten

    prep = tmp_path / "prep" / "lev"
    run_pipeline(vlpbek_bestand, prep)
    # Eén contract dat altijd één error oplevert.
    altijd_fout = contracten.Controle(
        "Test", "error", lambda star: iter([("dim_levering", "x", 1)])
    )
    monkeypatch.setattr(contracten, "CONTROLES", (altijd_fout,))
    with pytest.raises(KwaliteitsFout):
        run_star([prep], tmp_path / "out")
    rapport = json.loads((tmp_path / "out" / QUALITY_JSON).read_text(encoding="utf-8"))
    assert rapport["star"]["status"] == STATUS_FAIL
    assert rapport["leveringen"][0]["status"] == "ok"
```

Run: `uv run pytest tests/test_pipeline.py::test_star_contractbreuk_is_fail -v`
Expected: FAIL (`_star_meldingen` is nog leeg, dus geen `KwaliteitsFout`)

- [ ] **Step 4: Wire the register into `pipeline.py`**

```python
from ho_bekostiging_bestanden import contracten
from ho_bekostiging_bestanden.kwaliteit import STAR_BRON  # bij de bestaande kwaliteit-import


def _star_meldingen(star: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Meldingen van de star-contracten (``contracten.py``)."""
    return met_bron(contracten.controleer_star(star), STAR_BRON)
```

Importeer de module (`contracten.controleer_star`) en niet de functie, zodat de monkeypatch op `contracten.CONTROLES` werkt. `controleer_star` leest `CONTROLES` op het moment van aanroepen, dus dat werkt.

Run: `uv run pytest -q`
Expected: alles groen, inclusief `test_scenarios` (het scenario met alleen HISBEK heeft lege feittabellen: de contracten mogen dan niets melden).

- [ ] **Step 5: Lint-gate**

Run: `uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: groen

- [ ] **Step 6: Commit (alleen na akkoord gebruiker)**

```bash
git add src/ho_bekostiging_bestanden/contracten.py src/ho_bekostiging_bestanden/pipeline.py tests/
git commit -m "feat(#20): register met star-contracten (uniciteit, lege sleutels, koppelingen)"
```

---

### Task 4: `quality.json` met provenance en dekking (#21)

**Files:**
- Create: `src/ho_bekostiging_bestanden/metadata/quality.schema.json`
- Create: `tests/test_quality_json.py`
- Modify: `src/ho_bekostiging_bestanden/kwaliteit.py` (`bouw_rapport`, `dekking`, `_provenance`)
- Modify: `src/ho_bekostiging_bestanden/pipeline.py` (`_levering_tabel`, `run_pipeline`, `_bouw_star`)
- Modify: `src/ho_bekostiging_bestanden/star.py` (`DIM_LEVERING_SCHEMA`)
- Modify: `app/_utils.py` (`kwaliteitsbanner`), `app/pages/dashboard.py:169`, `app/pages/resultaten.py:33`, `app/_tabel_docs.py` (dim_levering)
- Modify: `pyproject.toml` (dev-dependency `jsonschema`)
- Modify tests: `tests/test_pipeline.py:26-34`, `tests/test_kwaliteit.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: `bouw_rapport`, `schrijf_rapport`, `lees_status` (Task 2); `SCHEMA_PER_LEVERING` (ingest); `load_schema` (metadata); `LABEL_COL`.
- Produces:
  - `bouw_rapport(meldingen: pl.DataFrame, dim_levering: pl.DataFrame, fouten_toegestaan: bool, dekking: list[dict[str, Any]]) -> dict[str, Any]` (nieuwe parameter `dekking`)
  - `dekking(stacked: dict[str, pl.DataFrame], dim_levering: pl.DataFrame) -> list[dict[str, Any]]`
  - `QUALITY_SCHEMA_VERSIE = 1`, `SHA256_KOLOM = "Sha256"`
  - kolom `Sha256` in `LEVERING` en `dim_levering`
  - `app/_utils.kwaliteitsbanner() -> None`

- [ ] **Step 1: Add jsonschema**

Run: `uv add --dev jsonschema`
Expected: `pyproject.toml` en `uv.lock` bijgewerkt. Controleer dat het in dezelfde dev-groep staat die CI met `uv sync --group dev` installeert.

- [ ] **Step 2: Failing tests**

`tests/test_quality_json.py`:

```python
import hashlib
import json
from importlib.resources import files

import jsonschema
import polars as pl

from ho_bekostiging_bestanden.kwaliteit import QUALITY_JSON
from ho_bekostiging_bestanden.pipeline import verwerk_alles
from ho_bekostiging_bestanden.stack import LABEL_COL

from .conftest import DEMO_RAW

SCHEMA = json.loads(
    files("ho_bekostiging_bestanden.metadata")
    .joinpath("quality.schema.json")
    .read_text(encoding="utf-8")
)


def _demo(tmp_path):
    resultaat = verwerk_alles(DEMO_RAW, tmp_path / "prep", tmp_path / "out")
    rapport = json.loads((tmp_path / "out" / QUALITY_JSON).read_text(encoding="utf-8"))
    return resultaat, rapport


def test_demo_rapport_valideert_tegen_schema(tmp_path):
    _, rapport = _demo(tmp_path)
    jsonschema.validate(rapport, SCHEMA)
    assert rapport["schema_version"] == 1
    assert rapport["provenance"]["pakketversie"]


def test_sha256_per_levering_klopt(tmp_path):
    _, rapport = _demo(tmp_path)
    for lev in rapport["leveringen"]:
        bron = DEMO_RAW / lev["bestandsnaam"]
        assert lev["sha256"] == hashlib.sha256(bron.read_bytes()).hexdigest()


def test_dekking_telt_rijen_per_levering_en_recordsoort(tmp_path):
    resultaat, rapport = _demo(tmp_path)
    brd = next(
        d for d in rapport["dekking"]
        if d["recordsoort"] == "BRD" and d["levering"].startswith("VLPBEK_2025")
    )
    verwacht = pl.read_parquet(
        tmp_path / "prep" / "VLPBEK_2025_20240115_99XX" / "BRD.parquet"
    ).height
    assert brd["rijen"] == verwacht
    # HISBEK kent geen BRD: die combinatie hoort er niet in.
    assert not any(
        d["levering"].startswith("HISBEK") and d["recordsoort"] == "BRD"
        for d in rapport["dekking"]
    )


def test_lege_map_valideert_tegen_schema(tmp_path):
    (tmp_path / "raw").mkdir()
    verwerk_alles(tmp_path / "raw", tmp_path / "prep", tmp_path / "out")
    rapport = json.loads((tmp_path / "out" / QUALITY_JSON).read_text(encoding="utf-8"))
    jsonschema.validate(rapport, SCHEMA)
    assert rapport["leveringen"] == [] and rapport["dekking"] == []


def test_schema_is_strikt(tmp_path):
    _, rapport = _demo(tmp_path)
    rapport["onbekend_veld"] = 1
    try:
        jsonschema.validate(rapport, SCHEMA)
    except jsonschema.ValidationError:
        return
    raise AssertionError("schema accepteert onbekende velden")
```

In `tests/test_pipeline.py:26-34`: voeg `"Sha256": hashlib.sha256(vlpbek_bestand.read_bytes()).hexdigest(),` toe aan de verwachte `LEVERING`-rij (import `hashlib`).

In `tests/test_kwaliteit.py`: geef in `test_rapport_round_trip_met_niet_ascii` de parameter `dekking=[]` mee aan `bouw_rapport`, en gebruik een `dim_levering` met de kolommen `LABEL_COL`, `Bestandsnaam` en `Sha256` (waarden `None` mag).

Run: `uv run pytest tests/test_quality_json.py tests/test_pipeline.py tests/test_kwaliteit.py -v`
Expected: FAIL (schemabestand ontbreekt, geen `Sha256`, `dekking` is onbekend)

- [ ] **Step 3: Write the JSON Schema**

`src/ho_bekostiging_bestanden/metadata/quality.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "HO-bekostigingsbestanden quality.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "status", "fouten_toegestaan", "total_errors",
               "total_warnings", "provenance", "leveringen", "star", "dekking"],
  "$defs": {
    "status": {"enum": ["ok", "warn", "fail"]},
    "melding": {
      "type": "object",
      "additionalProperties": false,
      "required": ["controle", "recordsoort", "melding", "aantal", "ernst"],
      "properties": {
        "controle": {"type": "string"},
        "recordsoort": {"type": "string"},
        "melding": {"type": "string"},
        "aantal": {"type": "integer", "minimum": 0},
        "ernst": {"enum": ["error", "warning"]}
      }
    },
    "meldingen": {"type": "array", "items": {"$ref": "#/$defs/melding"}}
  },
  "properties": {
    "schema_version": {"const": 1},
    "status": {"$ref": "#/$defs/status"},
    "fouten_toegestaan": {"type": "boolean"},
    "total_errors": {"type": "integer", "minimum": 0},
    "total_warnings": {"type": "integer", "minimum": 0},
    "provenance": {
      "type": "object",
      "additionalProperties": false,
      "required": ["pakketversie", "python", "polars", "aangemaakt"],
      "properties": {
        "pakketversie": {"type": "string"},
        "python": {"type": "string"},
        "polars": {"type": "string"},
        "aangemaakt": {"type": "string", "format": "date-time"}
      }
    },
    "leveringen": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["levering", "bestandsnaam", "sha256", "status", "meldingen"],
        "properties": {
          "levering": {"type": "string"},
          "bestandsnaam": {"type": ["string", "null"]},
          "sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
          "status": {"$ref": "#/$defs/status"},
          "meldingen": {"$ref": "#/$defs/meldingen"}
        }
      }
    },
    "star": {
      "type": "object",
      "additionalProperties": false,
      "required": ["status", "meldingen"],
      "properties": {
        "status": {"$ref": "#/$defs/status"},
        "meldingen": {"$ref": "#/$defs/meldingen"}
      }
    },
    "dekking": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["levering", "recordsoort", "rijen"],
        "properties": {
          "levering": {"type": "string"},
          "recordsoort": {"type": "string"},
          "rijen": {"type": "integer", "minimum": 0}
        }
      }
    }
  }
}
```

Controleer dat `metadata/` als package-data meegaat (hatchling neemt alles onder `src/ho_bekostiging_bestanden` mee; de TOML's en CSV's gaan al zo mee).

- [ ] **Step 4: Sha256 in LEVERING and dim_levering**

`pipeline.py`:
- `import hashlib`
- `_levering_tabel(info, vlp, schema_name, gepseudonimiseerd, sha256: str)`: voeg `"Sha256": [sha256]` en `"Sha256": pl.Utf8` toe (direct na `Bestandsnaam`).
- In `run_pipeline`: `sha256 = hashlib.sha256(Path(source).read_bytes()).hexdigest()` en die doorgeven.

`star.py`: `DIM_LEVERING_SCHEMA` krijgt `"Sha256": pl.Utf8` na `"Bestandsnaam"`. De bestaande code voor ontbrekende kolommen vult oude prepared-mappen met null.

`app/_tabel_docs.py`, `dim_levering` → `"wat"`: voeg toe "…, de sha256 van het bronbestand (om na te gaan welk bestand precies verwerkt is) en of BSN…". Draai `uv run pytest tests/test_app.py::test_tabel_docs_compleet`.

- [ ] **Step 5: Dekking and provenance in `kwaliteit.py`**

```python
import platform
from datetime import datetime

from ho_bekostiging_bestanden import __version__
from ho_bekostiging_bestanden.ingest import SCHEMA_PER_LEVERING
from ho_bekostiging_bestanden.metadata import load_schema

QUALITY_SCHEMA_VERSIE = 1
SHA256_KOLOM = "Sha256"


def dekking(
    stacked: dict[str, pl.DataFrame], dim_levering: pl.DataFrame
) -> list[dict[str, Any]]:
    """Rijen per levering × recordsoort uit het schema van die soort levering.

    Recordsoorten komen uit de schema-TOML's; een recordsoort zonder rijen
    telt als 0, zodat een ontbrekend deel van de levering zichtbaar is.
    """
    uitkomst = []
    for label, soort in dim_levering.select(LABEL_COL, "SoortLevering").iter_rows():
        schema_naam = SCHEMA_PER_LEVERING.get(soort) if soort else None
        if schema_naam is None:
            continue
        for rs in load_schema(schema_naam):
            df = stacked.get(rs)
            rijen = 0 if df is None else df.filter(pl.col(LABEL_COL) == label).height
            uitkomst.append({"levering": label, "recordsoort": rs, "rijen": rijen})
    return uitkomst


def _provenance() -> dict[str, str]:
    return {
        "pakketversie": __version__,
        "python": platform.python_version(),
        "polars": pl.__version__,
        "aangemaakt": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
```

Controleer dat `ho_bekostiging_bestanden/__init__.py` niets uit `kwaliteit` importeert (geen cyclus); nu bevat hij alleen `__version__`.

`bouw_rapport` krijgt `dekking: list[dict[str, Any]]` als laatste parameter en wordt:

```python
    labels = dim_levering[LABEL_COL].to_list()
    labels += sorted(set(meldingen[BRON_KOLOM].to_list()) - set(labels) - {STAR_BRON})
    herkomst = {
        rij[LABEL_COL]: rij
        for rij in dim_levering.select(
            LABEL_COL,
            *(k for k in ("Bestandsnaam", SHA256_KOLOM) if k in dim_levering.columns),
        ).iter_rows(named=True)
    }
    return {
        "schema_version": QUALITY_SCHEMA_VERSIE,
        "status": status(meldingen),
        "fouten_toegestaan": fouten_toegestaan,
        "total_errors": aantal(meldingen, ERNST_ERROR),
        "total_warnings": aantal(meldingen, ERNST_WARNING),
        "provenance": _provenance(),
        "leveringen": [
            {
                "levering": label,
                "bestandsnaam": herkomst.get(label, {}).get("Bestandsnaam"),
                "sha256": herkomst.get(label, {}).get(SHA256_KOLOM),
                **_onderdeel(meldingen, label),
            }
            for label in labels
        ],
        "star": _onderdeel(meldingen, STAR_BRON),
        "dekking": dekking,
    }
```

`pipeline._bouw_star`: `bouw_rapport(meldingen, star["dim_levering"], fouten_toegestaan, dekking(stacked, star["dim_levering"]))` (import `dekking`).

Run: `uv run pytest tests/test_quality_json.py tests/test_pipeline.py tests/test_kwaliteit.py -v`
Expected: PASS

- [ ] **Step 6: Failing AppTest for the banner**

In `tests/test_app.py`:

```python
@pytest.mark.parametrize("pagina", ["dashboard", "resultaten"])
def test_banner_bij_fail(app_config, pagina):
    uit = app_config / "out"
    uit.mkdir(parents=True, exist_ok=True)
    (uit / "quality.json").write_text(
        json.dumps({"status": "fail", "total_errors": 2}), encoding="utf-8"
    )
    at = _pagina(pagina).run()
    assert not at.exception
    assert any("Kwaliteitsstatus fail" in e.value for e in at.error)


def test_geen_banner_zonder_rapport(app_config):
    at = _pagina("resultaten").run()
    assert not at.error
```

Run: `uv run pytest tests/test_app.py -v`
Expected: FAIL (er is nog geen banner)

- [ ] **Step 7: Implement the banner**

`app/_utils.py`:

```python
from ho_bekostiging_bestanden.kwaliteit import (
    QUALITY_JSON,
    STATUS_FAIL,
    STATUS_WARN,
    lees_status,
)


def kwaliteitsbanner() -> None:
    """Toon de kwaliteitsstatus van het laatste star schema, als die niet ok is."""
    pad = output_dir() / QUALITY_JSON
    if not pad.exists():
        return
    status, fouten = lees_status(pad)
    if status == STATUS_FAIL:
        st.error(
            f"Kwaliteitsstatus fail: {fouten} error(s). De cijfers zijn niet "
            f"betrouwbaar; zie {QUALITY_JSON} of verwerk opnieuw op de Home-pagina."
        )
    elif status == STATUS_WARN:
        st.warning(f"Kwaliteitsstatus warn: er zijn waarschuwingen; zie {QUALITY_JSON}.")
```

(`_utils.py` importeert `streamlit as st` al als `pseudonimiseringssleutel` het gebruikt; anders toevoegen.)

Roep `kwaliteitsbanner()` aan direct na `st.title("Dashboard")` in `dashboard.py` en na `st.title("Resultaten")` in `resultaten.py` (import uit `_utils`). Er wijzigt geen grafiek, dus `_chart_docs.py` hoeft niet bij.

Run: `uv run pytest tests/test_app.py -v`
Expected: PASS

- [ ] **Step 8: Full verification**

Run: `uv run pytest -q` en `uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: alles groen.

Controleer ook handmatig de CLI-keten op de demo, in een console met cp1252:

```powershell
$t="$env:TEMP\ho-kw"; Remove-Item -Recurse -Force $t -ErrorAction SilentlyContinue
foreach ($f in Get-ChildItem data/01-raw/demo -File) { uv run ho verwerk $f.FullName "$t\prep\$($f.BaseName)" --geen-pseudonimisering; "exit=$LASTEXITCODE" }
uv run ho star (Get-ChildItem "$t\prep" -Directory).FullName --output "$t\out"; "exit=$LASTEXITCODE"
Get-Content "$t\out\quality.json" -Encoding utf8 | Select-Object -First 15
```

Expected: overal exit 0, `"status": "ok"`.

- [ ] **Step 9: Commit (alleen na akkoord gebruiker)**

```bash
git add src/ho_bekostiging_bestanden/ app/ tests/ pyproject.toml uv.lock
git commit -m "feat(#21): quality.json met provenance, sha256 per levering en dekking"
```

---

### Afronding

- [ ] README: sectie CLI aanvullen met exitcodes (0/1/3), `--allow-quality-errors` en `quality.json`; sectie datamodel: `Sha256` in `dim_levering`. De spec-sectie "Open punten" en de README niet tegenspreken.
- [ ] Spec en plan meecommitten (na akkoord gebruiker).
- [ ] Push en PR (na akkoord gebruiker) met "Closes #19, #20, #21, #22" en "Part of #18".
