# ho-bekostiging-bestanden v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een Python-repo die DUO HO-analysebestanden (VLPBEK, DEFBEK, HISBEK) inleest, decodeert, valideert en exporteert naar Parquet en een star schema, met CLI en Streamlit-app, opgezet zoals `cedanl/mbo-bekostiging-bestanden`.

**Architecture:** Een schemagedreven pipeline: TOML-veldindelingen per recordsoort sturen ingest, decode en validate. Elke levering wordt een prepared-map met Parquet per recordsoort plus de tabellen `LEVERING` en `VALIDATIE`. Stack voegt de prepared-mappen samen, star bouwt 5 dimensies en 4 feittabellen, `indicatoren.py` rekent de dashboardcijfers uit, en de app toont alleen.

**Tech Stack:** Python 3.13, uv, Polars, Streamlit, pytest, ruff, ty, hatchling.

**Spec:** `docs/superpowers/specs/2026-09-29-ho-bekostiging-bestanden-design.md`

**Referentie-implementatie:** `C:\Users\Aslam\Projects\mbo-bekostiging-bestanden`. Neem de stijl, docstrings en naamgeving daarvan over (Nederlandstalige docstrings, Google-stijl `Args/Returns/Raises`).

**Repo-root:** `C:\Users\Aslam\Projects\ho-bekostiging-bestanden`. Alle paden in dit plan zijn relatief ten opzichte van die map. Commando's draaien vanuit die map.

## Global Constraints

- Python `>=3.13`; dependencies: `polars>=1.0`, `streamlit>=1.40`; dev: `pytest>=8.0`, `ruff>=0.6`, `ty>=0.0.0a1`.
- Package `ho_bekostiging_bestanden` in `src/`; CLI-script `ho = "ho_bekostiging_bestanden.cli:main"`.
- ruff: `line-length = 88`, `target-version = "py313"`, lint `["E", "F", "I", "UP", "B"]`.
- Veldscheidingsteken `|`; datums `jjjjmmdd`; booleans `J`/`N`; UTF-8 (met terugval op latin-1).
- Veldnamen in PascalCase volgens de PvE; de instellingscode heet overal `BRIN` (hoofdletters, zoals bij MBO).
- Geen hardcoded waarden midden in de code: constanten bovenaan de module, of in `metadata/` of `app/config.toml`.
- Kolom `CodeBekostigingstatus` blijft tekst (bijvoorbeeld `"na,ti"`). Nergens komen list-kolommen voor in geëxporteerde tabellen.
- Natuurlijke sleutels: `levering`, `_persoon_id`, `BRIN`, `Opleidingscode`, `Code`, `_feit_id`.
- Elke soort levering is optioneel; alles moet ook werken zonder HISBEK.
- Geen echte persoonsgegevens in git; alleen synthetische demo-data in `data/01-raw/demo/`.
- Elke grafiek in het dashboard heeft een toelichting in `app/_chart_docs.py`; elke star-tabel een beschrijving in `app/_tabel_docs.py`.
- Draai altijd eerst `ruff format` en dan pas `ruff check` (E501 staat aan). Blijft er daarna een te lange regel over, bijvoorbeeld een lange f-string, splits die dan zelf op.
- Commit-berichten eindigen met de regel `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Alleen een HISBEK-bestand, of alleen één VLPBEK:** het star schema, de indicatoren en het dashboard moeten lege maar correct gevormde tabellen en een uitleg tonen, geen crash. Tests in Task 7 (`test_alleen_hisbek`), Task 8 (scenario's), Task 10 (`test_zonder_defbek_en_hisbek`) en Task 12 (`test_dashboard_met_een_levering`).
2. **Persoon met alleen een onderwijsnummer (BSN leeg):** `_persoon_id` moet dan het onderwijsnummer zijn, niet `null` of `""`. Test in Task 7 (`test_persoon_zonder_bsn_krijgt_onderwijsnummer`).
3. **CRLF-regeleinden en regels die zijn opgevuld tot 25 velden:** echte bestanden hebben allebei; de reader moet ze gewoon verwerken en git mag de demo-bestanden niet omzetten. Tests in Task 3 (`test_crlf_en_opvulling_verdwijnen`) en Task 9 (`.gitattributes` + `test_demo_in_git_is_actueel`).
4. **CSV-export en CSV-download:** `ho verwerk … --fmt csv` en de download in de app moeten werken; daarom zijn er geen list-kolommen. Tests in Task 5 (`test_export_gedecodeerde_frames[csv]`) en Task 6 (`test_run_pipeline_csv`).
5. **Bestandsnaam met kleine letters, `.CSV` of de PvE-spatie:** `defbek_2025_20240715_99xx.CSV` moet herkend worden. Test in Task 3 (`test_parse_bestandsnaam_varianten`).

## File Structure

```
ho-bekostiging-bestanden/
├── .devcontainer/{Dockerfile,devcontainer.json}
├── .github/workflows/ci.yml
├── .streamlit/config.toml
├── .gitignore  .python-version  AGENTS.md  CLAUDE.md  LICENSE  Makefile  README.md  pyproject.toml
├── app/
│   ├── main.py            # navigatie
│   ├── _utils.py          # config.toml lezen
│   ├── config.toml        # datapaden
│   ├── _chart_docs.py     # toelichting per grafiek
│   ├── _tabel_docs.py     # uitleg per star-tabel
│   └── pages/{home,dashboard,resultaten}.py
├── data/01-raw/demo/*.csv # synthetisch, door scripts/genereer_demo.py
├── data/02-prepared/demo/.gitkeep
├── data/03-output/demo/.gitkeep
├── scripts/genereer_demo.py
├── src/ho_bekostiging_bestanden/
│   ├── __init__.py
│   ├── metadata/__init__.py            # load_schema, load_codelijst
│   ├── metadata/analyse_schema.toml    # VLP/BLB/BRD/BRR/SLR
│   ├── metadata/hisbek_schema.toml     # VLP/HRD/HRR/SLR
│   ├── metadata/bekostigingstatus.csv  # 34 codes
│   ├── metadata/opleidingsniveau.csv … # overige codelijsten
│   ├── ingest.py  decode.py  validate.py  export.py
│   ├── pipeline.py  stack.py  star.py  indicatoren.py  cli.py
└── tests/
    ├── conftest.py
    ├── fixtures/          # kleine handgemaakte bestanden
    └── test_*.py
```

---
### Task 1: Repo-skelet en tooling

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.gitignore`, `LICENSE`, `AGENTS.md`, `CLAUDE.md`, `Makefile`, `.streamlit/config.toml`, `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`, `.github/workflows/ci.yml`, `src/ho_bekostiging_bestanden/__init__.py`, `data/02-prepared/demo/.gitkeep`, `data/03-output/demo/.gitkeep`
- Test: `tests/test_package.py`

**Interfaces:**
- Produces: importeerbaar package `ho_bekostiging_bestanden` met `__version__ = "0.1.0"`.

- [ ] **Step 1: Kopieer de tooling-bestanden die identiek zijn aan MBO**

```bash
MBO=../mbo-bekostiging-bestanden
mkdir -p .devcontainer .github/workflows .streamlit src/ho_bekostiging_bestanden tests data/02-prepared/demo data/03-output/demo data/01-raw/demo
cp $MBO/.python-version $MBO/LICENSE $MBO/Makefile .
cp $MBO/.streamlit/config.toml .streamlit/
cp $MBO/.devcontainer/Dockerfile $MBO/.devcontainer/devcontainer.json .devcontainer/
cp $MBO/.github/workflows/ci.yml .github/workflows/
touch data/02-prepared/demo/.gitkeep data/03-output/demo/.gitkeep
```

Voeg daarna in `.github/workflows/ci.yml` direct na de stap `Lint` een formatcontrole toe:

```yaml
      - name: Format
        run: uv run ruff format --check .
```

- [ ] **Step 2: Schrijf `pyproject.toml`**

```toml
[project]
name = "ho-bekostiging-bestanden"
version = "0.1.0"
description = "Leest DUO HO-bekostigingsbestanden in en zet ze om naar schone, onderzoeksklare data."
readme = "README.md"
requires-python = ">=3.13"
license = { text = "MIT" }
authors = [{ name = "CEDA", email = "ceda@cedanl.org" }]
dependencies = [
    "polars>=1.0",
    "streamlit>=1.40",
]

[project.scripts]
ho = "ho_bekostiging_bestanden.cli:main"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.6",
    "ty>=0.0.0a1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ho_bekostiging_bestanden"]

[tool.uv]
package = true

[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ty.environment]
python-version = "3.13"
```

- [ ] **Step 3: Schrijf `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
.uv_cache/
*.egg-info/
.pytest_cache/
.ruff_cache/

# Data
# 01-raw: echte data genegeerd, alleen demo-bronbestanden in git
data/01-raw/*
!data/01-raw/demo/

# 02-prepared en 03-output: gegenereerde output, nooit in git
data/02-prepared/**
!data/02-prepared/**/
!data/02-prepared/**/.gitkeep
data/03-output/**
!data/03-output/**/
!data/03-output/**/.gitkeep

# Lokale referentiedocumenten (PvE e.d.)
*.pdf

# OS / editor
.DS_Store
.idea/
.vscode/

# Make dev/stop (Streamlit)
.streamlit/.dev.pid
.streamlit/.dev.log
```

- [ ] **Step 4: Schrijf `AGENTS.md`** met als enige inhoud:

```
CLAUDE.md
```

- [ ] **Step 5: Schrijf `CLAUDE.md`**

```markdown
# ho-bekostiging-bestanden

## Overview
Ingestion-repo (Type 1). Leest ruwe DUO HO-bekostigingsbestanden (analysebestand
VLPBEK/DEFBEK en HISBEK) in en zet ze om naar schone, onderzoeksklare data.
Andere repos bouwen voort op de output. HO-tegenhanger van
`cedanl/mbo-bekostiging-bestanden`; houd beide repos zo gelijk mogelijk.
Pipeline-fase: `ingest > decode > validate > export > stack > star schema`.

## Standards
Volg de CEDA technische standaarden: https://github.com/cedanl/.github/tree/main/standards/README.md

## Coding Principles (voor alle LLM-bijdragers)
- **Modulair & onderhoudbaar** — herhalende logica hoort in een herbruikbare functie of module, niet inline gedupliceerd.
- **Geen hardcoded waarden** — paden, codes, labels en drempelwaarden komen uit config (`config.toml`, constanten bovenaan het bestand, `metadata/`, of parameters). Nooit als magic string midden in de code.
- **Dynamisch** — lees kolomnamen, opties en lijsten uit de data of de schema's; neem ze niet over als vaste lijst tenzij ze écht stabiel zijn.
- **Boy Scout Principle** — laat elke file die je aanraakt schoner achter dan je hem aantrof.
- **Geen Tactical Tornado** — geen quick-fixes die technische schuld opbouwen.
- **Geen commit tenzij gevraagd** — implementeer lokaal en meld wat er gedaan is; wacht op een expliciete commit-opdracht van de gebruiker.
- **Grafiektoelichtingen bijhouden** — bij elke aanpassing aan een grafiek in `app/pages/dashboard.py`: werk `app/_chart_docs.py` bij. Een grafiek zonder toelichting is niet af.
- **Werkwijze** — nieuwe features via de superpowers-flow: spec (`docs/superpowers/specs/`) → plan (`docs/superpowers/plans/`) → TDD.

## Tech Stack
- Python 3.13, uv voor dependency-management
- Polars voor data-verwerking
- Streamlit voor de interactieve interface
- pytest (tests), ruff (lint/format), ty (type checking)

## Project Structure
```
ho-bekostiging-bestanden/
├── data/01-raw/demo/          # Synthetische demo-bestanden (in git)
├── scripts/genereer_demo.py   # Maakt de demo-bestanden (vaste seed)
├── src/ho_bekostiging_bestanden/
│   ├── ingest.py  decode.py  validate.py  export.py
│   ├── pipeline.py  stack.py  star.py  indicatoren.py  cli.py
│   └── metadata/              # Veldindelingen (TOML) en codelijsten (CSV)
├── app/                       # Streamlit (geen bedrijfslogica)
└── tests/
```

## How to Run
- Dependencies: `uv sync`
- Tests: `uv run pytest`
- App: `uv run streamlit run app/main.py`
- CLI: `uv run ho verwerk <bestand> <doelmap>` en `uv run ho star <mappen…> --output <map>`

## Data
- **Input**: DUO-analysebestanden `VLPBEK_JJJJ_EEJJMMDD_99XX.CSV`, `DEFBEK_…`, `HISBEK_…`.
  Multi-record, `|`-gescheiden (VLP/BLB/BRD/BRR/SLR, resp. VLP/HRD/HRR/SLR).
  Bron: PvE HO-instelling – DUO v26.3.1, bijlagen 8 en 10.
- **Output**: Parquet in `data/02-prepared/` en star schema in `data/03-output/`.
- Echte data is gitignored; alleen synthetische demo-data in `data/01-raw/demo/`.
- Privacy: geen persoonsgegevens committen.
```

- [ ] **Step 6: Schrijf `src/ho_bekostiging_bestanden/__init__.py`**

```python
"""Inlezen en omzetten van DUO HO-bekostigingsbestanden."""

__version__ = "0.1.0"
```

- [ ] **Step 7: Schrijf de falende test `tests/test_package.py`**

```python
import ho_bekostiging_bestanden


def test_package_heeft_versie():
    assert ho_bekostiging_bestanden.__version__ == "0.1.0"
```

- [ ] **Step 8: Installeer en draai de tests**

Run: `uv sync && uv run pytest -v`
Expected: `1 passed`

- [ ] **Step 9: Lint en typecheck**

Run: `uv run ruff format . && uv run ruff check . && uv run ty check`
Expected: geen fouten.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "chore: repo-skelet en tooling (zoals mbo-bekostiging-bestanden)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Metadata — veldindelingen en codelijsten

**Files:**
- Create: `src/ho_bekostiging_bestanden/metadata/__init__.py`
- Create: `src/ho_bekostiging_bestanden/metadata/analyse_schema.toml`
- Create: `src/ho_bekostiging_bestanden/metadata/hisbek_schema.toml`
- Create: `src/ho_bekostiging_bestanden/metadata/bekostigingstatus.csv` en de overige codelijst-CSV's (Step 6)
- Test: `tests/test_metadata.py`

**Interfaces:**
- Produces:
  - `SCHEMA_DIR: Path`
  - `load_schema(name: str) -> dict[str, dict]`: recordsoort → dict met `fields: list[str]` en optioneel `single_row: bool`, `date_fields`, `bool_fields`, `int_fields`, `float_fields`, `nvt_fields`, `required_fields` (alle `list[str]`) en `codelijsten: dict[str, str]` (veld → codelijstnaam). Namen: `"analyse"`, `"hisbek"`.
  - `schema_meta(name: str) -> dict`: de top-level scalaire sleutels (`schema_version`, `bron`).
  - `load_codelijst(name: str) -> pl.DataFrame`: alle kolommen `pl.Utf8`; minstens `Code` en `Omschrijving`.

Schemaconventies (gelden voor alle volgende taken):
- Het eerste veld is altijd `Recordsoort`.
- `nvt_fields`: de waarde `-1` betekent "n.v.t." (PvE §17.7.2).
- `codelijsten`: velden waarvan de waarden in `metadata/<naam>.csv` moeten voorkomen. Waarden met komma's (zoals `na,ti`) worden per code gecontroleerd.
- SLR-velden heten `Aantal<RS>records`; validate leidt daar dynamisch de te tellen recordsoort uit af.

- [ ] **Step 1: Schrijf de falende tests `tests/test_metadata.py`**

```python
import polars as pl
import pytest

from ho_bekostiging_bestanden.metadata import (
    SCHEMA_DIR,
    load_codelijst,
    load_schema,
    schema_meta,
)

SCHEMAS = ["analyse", "hisbek"]
_LIJST_SLEUTELS = [
    "date_fields",
    "bool_fields",
    "int_fields",
    "float_fields",
    "nvt_fields",
    "required_fields",
]


@pytest.mark.parametrize("naam", SCHEMAS)
def test_schema_laadt_met_recordsoort_eerst(naam):
    schema = load_schema(naam)
    assert {"VLP", "SLR"} <= set(schema)
    for rs, spec in schema.items():
        assert spec["fields"][0] == "Recordsoort", rs
        assert len(spec["fields"]) == len(set(spec["fields"])), rs


@pytest.mark.parametrize("naam", SCHEMAS)
def test_typevelden_bestaan_in_fields(naam):
    for rs, spec in load_schema(naam).items():
        velden = set(spec["fields"])
        for sleutel in _LIJST_SLEUTELS:
            assert set(spec.get(sleutel, [])) <= velden, (rs, sleutel)
        assert set(spec.get("codelijsten", {})) <= velden, rs


@pytest.mark.parametrize("naam", SCHEMAS)
def test_codelijsten_uit_schema_bestaan(naam):
    for spec in load_schema(naam).values():
        for lijst in spec.get("codelijsten", {}).values():
            assert (SCHEMA_DIR / f"{lijst}.csv").exists(), lijst


def test_veldaantallen_volgens_pve():
    analyse = load_schema("analyse")
    assert len(analyse["BLB"]["fields"]) == 21
    assert len(analyse["BRD"]["fields"]) == 25
    assert len(analyse["BRR"]["fields"]) == 24
    hisbek = load_schema("hisbek")
    assert len(hisbek["HRD"]["fields"]) == 30
    assert len(hisbek["HRR"]["fields"]) == 27


def test_schema_meta():
    assert schema_meta("analyse")["schema_version"] == "26.3.1"


def test_onbekend_schema_geeft_fout():
    with pytest.raises(FileNotFoundError):
        load_schema("bestaat_niet")


def test_bekostigingstatus_compleet():
    df = load_codelijst("bekostigingstatus")
    assert df.height == 34
    assert df["Code"].n_unique() == 34
    assert df["Groep"].null_count() == 0
    assert set(df["Bekostigd"].unique()) == {"J", "N"}
    bekostigd = set(df.filter(pl.col("Bekostigd") == "J")["Code"])
    assert bekostigd == {"pi", "pd", "pg", "pb", "pm", "po"}


def test_codelijst_kolommen_zijn_tekst():
    df = load_codelijst("opleidingsfase")
    assert df.schema["Code"] == pl.Utf8
    assert "1" in df["Code"].to_list()
```

- [ ] **Step 2: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_metadata.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named 'ho_bekostiging_bestanden.metadata'`

- [ ] **Step 3: Schrijf `src/ho_bekostiging_bestanden/metadata/__init__.py`**

```python
"""Metadata: veldindelingen en codelijsten voor de HO-bekostigingsbestanden."""

import tomllib
from functools import lru_cache
from pathlib import Path

import polars as pl

SCHEMA_DIR = Path(__file__).parent


@lru_cache
def _lees_toml(name: str) -> dict:
    schema_path = SCHEMA_DIR / f"{name}_schema.toml"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema niet gevonden: {schema_path}")
    with open(schema_path, "rb") as f:
        return tomllib.load(f)


def load_schema(name: str) -> dict[str, dict]:
    """Laad een schema-TOML en geef de recordsoort-entries terug.

    Args:
        name: Naam van het schema zonder extensie (``"analyse"`` of
              ``"hisbek"``). Laadt ``{name}_schema.toml`` uit ``metadata/``.

    Returns:
        Dict van recordsoort naar schema-dict (``fields``, ``date_fields``,
        ``bool_fields``, ``int_fields``, ``float_fields``, ``nvt_fields``,
        ``required_fields``, ``codelijsten``, ``single_row``).

    Raises:
        FileNotFoundError: Als het schema-bestand niet bestaat.
    """
    return {k: v for k, v in _lees_toml(name).items() if isinstance(v, dict)}


def schema_meta(name: str) -> dict:
    """Geef de top-level metadata van een schema (bijv. ``schema_version``)."""
    return {k: v for k, v in _lees_toml(name).items() if not isinstance(v, dict)}


@lru_cache
def _lees_codelijst(name: str) -> pl.DataFrame:
    pad = SCHEMA_DIR / f"{name}.csv"
    if not pad.exists():
        raise FileNotFoundError(f"Codelijst niet gevonden: {pad}")
    return pl.read_csv(pad, infer_schema=False)


def load_codelijst(name: str) -> pl.DataFrame:
    """Laad een codelijst uit ``metadata/{name}.csv``; alle kolommen als tekst.

    Raises:
        FileNotFoundError: Als de codelijst niet bestaat.
    """
    return _lees_codelijst(name).clone()
```

- [ ] **Step 4: Schrijf `src/ho_bekostiging_bestanden/metadata/analyse_schema.toml`**

```toml
# Veldschema voor het analysebestand voorlopige/definitieve bekostiging HO
# (VLPBEK / DEFBEK). Bron: PvE HO-instelling – DUO v26.3.1, bijlage 8 (§17.7).
# Alleen de huidige BLB-versie (niet de "_OUD"-versie van vóór sept. 2019).
schema_version = "26.3.1"
bron = "PvE HO-instelling – DUO, bijlage 8"

[VLP]
single_row      = true
fields          = ["Recordsoort", "BRIN", "Bekostigingsjaar", "DatumAanmaak"]
date_fields     = ["DatumAanmaak"]
int_fields      = ["Bekostigingsjaar"]
required_fields = ["Recordsoort", "BRIN", "Bekostigingsjaar", "DatumAanmaak"]

[BLB]
fields = [
    "Recordsoort", "Burgerservicenummer", "Onderwijsnummer",
    "DatumGraadBehaaldAD", "DatumGraadBehaaldADLG",
    "DatumGraadBehaaldBa", "DatumGraadBehaaldBaLG",
    "DatumGraadBehaaldMa", "DatumGraadBehaaldMaLG",
    "VerbruikAD", "VerbruikADLG", "VerbruikBA", "VerbruikBALG",
    "VerbruikMA", "VerbruikMALG",
    "AantalBekostigdeInschrijvingenBa", "AantalBekostigdeInschrijvingenBaLG",
    "AantalBekostigdeInschrijvingenMa", "AantalBekostigdeInschrijvingenMaLG",
    "AantalBekostigdeInschrijvingenBaLGnaGraadBaMa",
    "AantalBekostigdeInschrijvingenMaLGnaGraadMa",
]
date_fields = [
    "DatumGraadBehaaldAD", "DatumGraadBehaaldADLG",
    "DatumGraadBehaaldBa", "DatumGraadBehaaldBaLG",
    "DatumGraadBehaaldMa", "DatumGraadBehaaldMaLG",
]
int_fields = [
    "VerbruikAD", "VerbruikADLG", "VerbruikBA", "VerbruikBALG",
    "VerbruikMA", "VerbruikMALG",
    "AantalBekostigdeInschrijvingenBa", "AantalBekostigdeInschrijvingenBaLG",
    "AantalBekostigdeInschrijvingenMa", "AantalBekostigdeInschrijvingenMaLG",
    "AantalBekostigdeInschrijvingenBaLGnaGraadBaMa",
    "AantalBekostigdeInschrijvingenMaLGnaGraadMa",
]
nvt_fields = [
    "VerbruikAD", "VerbruikADLG", "VerbruikBA", "VerbruikBALG",
    "VerbruikMA", "VerbruikMALG",
    "AantalBekostigdeInschrijvingenBa", "AantalBekostigdeInschrijvingenBaLG",
    "AantalBekostigdeInschrijvingenMa", "AantalBekostigdeInschrijvingenMaLG",
    "AantalBekostigdeInschrijvingenBaLGnaGraadBaMa",
    "AantalBekostigdeInschrijvingenMaLGnaGraadMa",
]
required_fields = ["Recordsoort"]

[BRD]
fields = [
    "Recordsoort", "Burgerservicenummer", "Onderwijsnummer", "BRIN",
    "Inschrijvingvolgnummer", "Bekostigingsindicatie", "CodeBekostigingstatus",
    "Bekostigingsniveau", "Opleidingscode", "Opleidingsniveau", "Opleidingsfase",
    "DatumInschrijving", "DatumUitschrijving", "EersteInschrijving",
    "Inschrijvingsvorm", "Onderwijsvorm", "DatumEersteAanlevering",
    "Bekostigingsduur", "OpleidingOnderdeel", "Bekostigingscode",
    "IndicatieSectorLG", "IndicatieBaMa", "IndicatieAcademischZiekenhuis",
    "IndicatieNationaliteitsvoorwaardeSF", "IndicatieGBARelatie",
]
date_fields = ["DatumInschrijving", "DatumUitschrijving", "DatumEersteAanlevering"]
bool_fields = [
    "Bekostigingsindicatie", "EersteInschrijving", "IndicatieSectorLG",
    "IndicatieAcademischZiekenhuis", "IndicatieNationaliteitsvoorwaardeSF",
    "IndicatieGBARelatie",
]
int_fields = ["Bekostigingsduur"]
required_fields = [
    "Recordsoort", "BRIN", "Inschrijvingvolgnummer", "Bekostigingsindicatie",
    "CodeBekostigingstatus", "Opleidingscode", "Opleidingsniveau",
    "Opleidingsfase", "DatumInschrijving", "DatumUitschrijving",
    "EersteInschrijving", "Inschrijvingsvorm", "Onderwijsvorm",
    "DatumEersteAanlevering",
]

[BRD.codelijsten]
CodeBekostigingstatus = "bekostigingstatus"
Bekostigingsniveau    = "bekostigingsniveau"
Opleidingsniveau      = "opleidingsniveau"
Opleidingsfase        = "opleidingsfase"
Inschrijvingsvorm     = "inschrijvingsvorm"
Onderwijsvorm         = "onderwijsvorm"
OpleidingOnderdeel    = "opleidingonderdeel"
Bekostigingscode      = "bekostigingscode"
IndicatieBaMa         = "indicatiebama"

[BRR]
fields = [
    "Recordsoort", "Burgerservicenummer", "Onderwijsnummer", "BRIN",
    "Resultaatvolgnummer", "Bekostigingsindicatie", "CodeBekostigingstatus",
    "Bekostigingsniveau", "JointDegreeFactor", "Opleidingscode",
    "Opleidingsniveau", "Opleidingsfase", "EersteGraad", "DatumDiploma",
    "Onderwijsvorm", "DatumEersteAanlevering", "OpleidingOnderdeel",
    "Bekostigingscode", "IndicatieSectorLG", "IndicatieBaMa",
    "IndicatieAcademischZiekenhuis", "IndicatieGraadTeltVoorBekostigingsloopbaan",
    "IndicatieNationaliteitsvoorwaardeSF", "IndicatieGBARelatie",
]
date_fields = ["DatumDiploma", "DatumEersteAanlevering"]
bool_fields = [
    "Bekostigingsindicatie", "EersteGraad", "IndicatieSectorLG",
    "IndicatieAcademischZiekenhuis", "IndicatieGraadTeltVoorBekostigingsloopbaan",
    "IndicatieNationaliteitsvoorwaardeSF", "IndicatieGBARelatie",
]
float_fields = ["JointDegreeFactor"]
required_fields = [
    "Recordsoort", "BRIN", "Resultaatvolgnummer", "Bekostigingsindicatie",
    "CodeBekostigingstatus", "Bekostigingsniveau", "Opleidingscode",
    "Opleidingsniveau", "Opleidingsfase", "EersteGraad", "DatumDiploma",
    "Onderwijsvorm", "DatumEersteAanlevering",
    "IndicatieGraadTeltVoorBekostigingsloopbaan",
    "IndicatieNationaliteitsvoorwaardeSF", "IndicatieGBARelatie",
]

[BRR.codelijsten]
CodeBekostigingstatus = "bekostigingstatus"
Bekostigingsniveau    = "bekostigingsniveau"
Opleidingsniveau      = "opleidingsniveau"
Opleidingsfase        = "opleidingsfase"
Onderwijsvorm         = "onderwijsvorm"
OpleidingOnderdeel    = "opleidingonderdeel"
Bekostigingscode      = "bekostigingscode"
IndicatieBaMa         = "indicatiebama"

[SLR]
single_row      = true
fields          = ["Recordsoort", "AantalBLBrecords", "AantalBRDrecords", "AantalBRRrecords"]
int_fields      = ["AantalBLBrecords", "AantalBRDrecords", "AantalBRRrecords"]
required_fields = ["Recordsoort", "AantalBLBrecords", "AantalBRDrecords", "AantalBRRrecords"]
```

- [ ] **Step 5: Schrijf `src/ho_bekostiging_bestanden/metadata/hisbek_schema.toml`**

```toml
# Veldschema voor het bestand historische bekostiging HO (HISBEK).
# Bron: PvE HO-instelling – DUO v26.3.1, bijlage 10 (§19.7).
# Het VLP-record heeft hier geen bekostigingsjaar; dat staat per HRD/HRR-record.
schema_version = "26.3.1"
bron = "PvE HO-instelling – DUO, bijlage 10"

[VLP]
single_row      = true
fields          = ["Recordsoort", "BRIN", "DatumAanmaak"]
date_fields     = ["DatumAanmaak"]
required_fields = ["Recordsoort", "BRIN", "DatumAanmaak"]

[HRD]
fields = [
    "Recordsoort", "Burgerservicenummer", "Onderwijsnummer", "Bekostigingsjaar",
    "BRIN", "Inschrijvingvolgnummer", "Bekostigingsindicatie",
    "CodeBekostigingstatus", "Bekostigingsniveau", "Opleidingscode",
    "Opleidingsniveau", "Opleidingsfase", "DatumInschrijving",
    "DatumUitschrijving", "EersteInschrijving", "Inschrijvingsvorm",
    "Onderwijsvorm", "DatumEersteAanlevering", "Bekostigingsduur", "ECTS",
    "ECTSBekostigd", "OpleidingOnderdeel", "Bekostigingscode",
    "IndicatieSectorLG", "IndicatieBaMa", "IndicatieAcademischZiekenhuis",
    "DuitseDeelstaat", "IndicatieWoonplaatsVereiste",
    "IndicatieNationaliteitsvoorwaardeSF", "IndicatieGBARelatie",
]
date_fields = ["DatumInschrijving", "DatumUitschrijving", "DatumEersteAanlevering"]
bool_fields = [
    "Bekostigingsindicatie", "EersteInschrijving", "IndicatieSectorLG",
    "IndicatieAcademischZiekenhuis", "IndicatieWoonplaatsVereiste",
    "IndicatieNationaliteitsvoorwaardeSF", "IndicatieGBARelatie",
]
int_fields = ["Bekostigingsjaar", "Bekostigingsduur"]
float_fields = ["ECTS", "ECTSBekostigd"]
required_fields = [
    "Recordsoort", "Bekostigingsjaar", "BRIN", "Bekostigingsindicatie",
    "CodeBekostigingstatus", "Opleidingscode", "Opleidingsniveau",
    "Opleidingsfase", "DatumInschrijving", "EersteInschrijving",
    "Inschrijvingsvorm", "Onderwijsvorm",
]

[HRD.codelijsten]
CodeBekostigingstatus = "bekostigingstatus"
Bekostigingsniveau    = "bekostigingsniveau"
Opleidingsniveau      = "opleidingsniveau"
Opleidingsfase        = "opleidingsfase"
Inschrijvingsvorm     = "inschrijvingsvorm"
Onderwijsvorm         = "onderwijsvorm"
OpleidingOnderdeel    = "opleidingonderdeel"
Bekostigingscode      = "bekostigingscode"
IndicatieBaMa         = "indicatiebama"

[HRR]
fields = [
    "Recordsoort", "Burgerservicenummer", "Onderwijsnummer", "Bekostigingsjaar",
    "BRIN", "Resultaatvolgnummer", "Bekostigingsindicatie",
    "CodeBekostigingstatus", "Bekostigingsniveau", "JointDegreeFactor",
    "Opleidingscode", "Opleidingsniveau", "Opleidingsfase", "EersteGraad",
    "DatumDiploma", "Onderwijsvorm", "DatumEersteAanlevering",
    "OpleidingOnderdeel", "Bekostigingscode", "IndicatieSectorLG",
    "IndicatieBaMa", "IndicatieAcademischZiekenhuis",
    "IndicatieGraadTeltVoorBekostigingsloopbaan", "DuitseDeelstaat",
    "IndicatieWoonplaatsVereiste", "IndicatieNationaliteitsvoorwaardeSF",
    "IndicatieGBARelatie",
]
date_fields = ["DatumDiploma", "DatumEersteAanlevering"]
bool_fields = [
    "Bekostigingsindicatie", "EersteGraad", "IndicatieSectorLG",
    "IndicatieAcademischZiekenhuis", "IndicatieGraadTeltVoorBekostigingsloopbaan",
    "IndicatieWoonplaatsVereiste", "IndicatieNationaliteitsvoorwaardeSF",
    "IndicatieGBARelatie",
]
int_fields = ["Bekostigingsjaar"]
float_fields = ["JointDegreeFactor"]
required_fields = [
    "Recordsoort", "Bekostigingsjaar", "BRIN", "Bekostigingsindicatie",
    "CodeBekostigingstatus", "JointDegreeFactor", "Opleidingscode",
    "Opleidingsniveau", "Opleidingsfase", "EersteGraad",
    "IndicatieGraadTeltVoorBekostigingsloopbaan",
    "IndicatieNationaliteitsvoorwaardeSF",
]

[HRR.codelijsten]
CodeBekostigingstatus = "bekostigingstatus"
Bekostigingsniveau    = "bekostigingsniveau"
Opleidingsniveau      = "opleidingsniveau"
Opleidingsfase        = "opleidingsfase"
Onderwijsvorm         = "onderwijsvorm"
OpleidingOnderdeel    = "opleidingonderdeel"
Bekostigingscode      = "bekostigingscode"
IndicatieBaMa         = "indicatiebama"

[SLR]
single_row      = true
fields          = ["Recordsoort", "AantalHRDrecords", "AantalHRRrecords"]
int_fields      = ["AantalHRDrecords", "AantalHRRrecords"]
required_fields = ["Recordsoort", "AantalHRDrecords", "AantalHRRrecords"]
```

- [ ] **Step 6: Schrijf de codelijsten in `src/ho_bekostiging_bestanden/metadata/`**

Bron van alle waarden: PvE §17.7.3, §17.7.4 en §19.7.5. De kolom `Groep` in
`bekostigingstatus.csv` is een **eigen indeling** (rapport MBO-HO, bijlage B),
niet van DUO **[Te checken]**.

`bekostigingstatus.csv`:

```csv
Code,Omschrijving,Groep,Bekostigd
pi,De inschrijving wordt bekostigd,Wel bekostigd,J
pd,De inschrijving wordt deels bekostigd,Wel bekostigd,J
pg,De graad wordt bekostigd,Wel bekostigd,J
pb,"Ongedeelde opleiding: alleen de (impliciete) BA-graad wordt bekostigd, niet de MA-graad",Wel bekostigd,J
pm,"Ongedeelde opleiding: alleen de MA-graad wordt bekostigd, niet de (impliciete) BA-graad",Wel bekostigd,J
po,Ongedeelde opleiding: zowel de (impliciete) BA- als de MA-graad wordt bekostigd,Wel bekostigd,J
ex,Het betreft een extraneus-inschrijving,Status van de student,N
jk,Meerdere eerste inschrijvingen aangeleverd voor verschillende opleidingen,Status van de student,N
jl,Geen opleiding van eerste inschrijving (eerste inschrijving is N),Status van de student,N
jm,Meerdere eerste inschrijvingen voor dezelfde opleiding aan dezelfde instelling,Status van de student,N
na,De student voldoet niet aan het woonplaatsvereiste,Status van de student,N
nr,De student voldoet niet aan het nationaliteitsvereiste,Status van de student,N
nb,Niet bekostigd i.v.m. eerder behaalde graad/graden,Verbruik en limieten,N
nd,De student heeft al eerder een MA-graad behaald,Verbruik en limieten,N
nf,Maximaal aantal bekostigde inschrijvingen overschreden (rekening houdend met eerdere graden),Verbruik en limieten,N
ng,Maximaal aantal bekostigde inschrijvingen overschreden (nog geen graad behaald),Verbruik en limieten,N
nh,Ongedeelde opleiding: toegestane te bekostigen jaren MA verbruikt,Verbruik en limieten,N
ni,Ongedeelde opleiding: toegestane jaren MA in een uitzonderingscategorie verbruikt,Verbruik en limieten,N
nk,Toegestane te bekostigen jaren of studielast MA verbruikt,Verbruik en limieten,N
ne,Geen voor bekostiging relevante graad of een AD-graad,Graad-specifiek,N
np,Graad die niet voor bekostiging in aanmerking komt (opleidingsfase P of D of A),Graad-specifiek,N
ns,Aan verschillende instellingen op dezelfde dag een zelfde soort graad behaald,Graad-specifiek,N
nt,"Meerdere graden aan dezelfde instelling, slechts één wordt bekostigd",Graad-specifiek,N
no,Ongedeelde opleiding waarvan de behaalde graden (BA en MA) beide niet bekostigd worden,Graad-specifiek,N
mt,De graad is behaald na de peilperiode,Tijdvak,N
mu,De graad is behaald vóór de peilperiode,Tijdvak,N
mv,De inschrijving is niet geldig op de peildatum / valt buiten het bekostigingsjaar,Tijdvak,N
mw,Graad zonder bijbehorende op datum diploma geldige inschrijving,Tijdvak,N
ob,Datum diploma valt niet in de accreditatieperiode,Opleiding,N
oc,Het betreft geen geaccrediteerde opleiding,Opleiding,N
ti,De inschrijving is niet tijdig aangeleverd,Aanlevering,N
tg,De graad is niet tijdig aangeleverd,Aanlevering,N
nl,Aangeleverd met de markering om niet te bekostigen,Aanlevering,N
nc,Niet bekostigd vanuit de conversie naar HORS,Overig,N
```

`opleidingsniveau.csv`:

```csv
Code,Omschrijving
HBO-AD,HBO Associate Degree
HBO-BA,HBO Bachelor
HBO-MA,HBO Master
HBO-O,HBO Ongedeeld
WO-BA,WO Bachelor
WO-MA,WO Master
WO-O,WO Ongedeeld
```

`opleidingsfase.csv`:

```csv
Code,Omschrijving
1,Eerste fase
2,Tweede fase
A,Associate Degree
B,Bachelor
D,Propedeuse bachelor
I,Initiële opleiding
K,Kandidaats
L,Universitaire lerarenopleiding (ULO)
M,Master
P,Propedeuse
S,Schakelprogramma
T,Tussentijds doctoraal examen
V,Vervolg of voortgezette opleiding
W,Voortgezette opleiding
```

`inschrijvingsvorm.csv`:

```csv
Code,Omschrijving
E,Extraneus
S,Student
```

`onderwijsvorm.csv`:

```csv
Code,Omschrijving
VT,Voltijd
DT,Deeltijd
DU,Duaal
```

`bekostigingsniveau.csv`:

```csv
Code,Omschrijving
LAAG,Laag
HOOG,Hoog
TOP,Top
```

`opleidingonderdeel.csv`:

```csv
Code,Omschrijving
ECONOMIE,Economie
GEDRAG_EN_MAATSCHAPPIJ,Gedrag en maatschappij
GEZONDHEIDSZORG,Gezondheidszorg
LANDBOUW_EN_NATUURLIJKE_OMGEVING,Landbouw en natuurlijke omgeving
NATUUR,Natuur
ONDERWIJS,Onderwijs
RECHT,Recht
SECTOROVERSTIJGEND,Sectoroverstijgend
TAAL_EN_CULTUUR,Taal en cultuur
TECHNIEK,Techniek
```

`bekostigingscode.csv`:

```csv
Code,Omschrijving
BEKOSTIGD,Bekostigd
OPEN_BESTEL,Open bestel (experiment)
```

`indicatiebama.csv`:

```csv
Code,Omschrijving
B,Bachelor
M,Master
A,Master met impliciete bachelor
D,Associate Degree
```

- [ ] **Step 7: Run de tests**

Run: `uv run pytest tests/test_metadata.py -v`
Expected: alle tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/ho_bekostiging_bestanden/metadata tests/test_metadata.py
git commit -m "feat(metadata): veldindelingen analysebestand/HISBEK en codelijsten uit PvE

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Ingest — bestandsnaam ontleden en multi-record inlezen

**Files:**
- Create: `src/ho_bekostiging_bestanden/ingest.py`
- Create: `tests/conftest.py` (testhelpers die alle volgende taken gebruiken)
- Test: `tests/test_ingest.py`

**Interfaces:**
- Consumes: `load_schema(name)` uit Task 2.
- Produces (in `ingest.py`):
  - `SCHEMA_PER_LEVERING: dict[str, str] = {"VLPBEK": "analyse", "DEFBEK": "analyse", "HISBEK": "hisbek"}`
  - `LEVERING = "LEVERING"`, `VALIDATIE = "VALIDATIE"`: tabelnamen die de pipeline (Task 6) vult en star (Task 7) leest.
  - `MELDINGEN: str = "_MELDINGEN"`: sleutel van het meldingenframe (kolommen `Regelnummer: Int64`, `Recordsoort: Utf8`, `Melding: Utf8`).
  - `@dataclass(frozen=True) class Bestandsinfo`: `soort: str`, `bekostigingsjaar: int`, `datum_aanmaak: date`, `brin: str`, `bestandsnaam: str`.
  - `parse_bestandsnaam(path: str | Path) -> Bestandsinfo | None`
  - `read_multi_record_csv(path: str | Path, schema_name: str) -> dict[str, pl.DataFrame]`: recordsoort → DataFrame (alle kolommen `Utf8`, lege velden als `""`), plus altijd de sleutel `MELDINGEN`.
- Produces (in `tests/conftest.py`): `maak_regel(schema_naam, rs, **waarden) -> str`, `schrijf_bestand(map_, naam, regels) -> Path`, `analyse_regels(jaar=2025, statussen=None) -> list[str]`, `hisbek_regels() -> list[str]`, en de fixtures `vlpbek_bestand`, `hisbek_bestand`.

- [ ] **Step 1: Schrijf `tests/conftest.py`**

```python
"""Gedeelde testhelpers: bouw kleine, realistische DUO-bestanden in tmp-mappen.

Regels worden opgebouwd vanuit de schema-TOML's, zodat tests meebewegen met de
veldindeling. Bestanden krijgen CRLF-regeleinden en worden opgevuld tot
minstens 25 velden, zoals de echte DUO-bestanden.
"""

from pathlib import Path

import pytest

from ho_bekostiging_bestanden.metadata import load_schema

PAD_TOT = 25  # aantal velden waarop DUO elke regel opvult


def maak_regel(schema_naam: str, rs: str, **waarden: str) -> str:
    """Bouw één `|`-regel; niet opgegeven velden blijven leeg."""
    velden = load_schema(schema_naam)[rs]["fields"]
    onbekend = set(waarden) - set(velden)
    if onbekend:
        raise KeyError(f"Onbekende velden voor {rs}: {sorted(onbekend)}")
    return "|".join(
        rs if veld == "Recordsoort" else waarden.get(veld, "") for veld in velden
    )


def schrijf_bestand(map_: Path, naam: str, regels: list[str]) -> Path:
    """Schrijf regels met CRLF, opgevuld tot minstens ``PAD_TOT`` velden."""
    opgevuld = []
    for regel in regels:
        tekort = PAD_TOT - 1 - regel.count("|")
        opgevuld.append(regel + "|" * max(tekort, 0))
    pad = map_ / naam
    pad.write_bytes(("\r\n".join(opgevuld) + "\r\n").encode("utf-8"))
    return pad


def _brd(bsn: str, onr: str, brin: str, volgnr: str, ind: str, code: str) -> str:
    return maak_regel(
        "analyse", "BRD",
        Burgerservicenummer=bsn, Onderwijsnummer=onr, BRIN=brin,
        Inschrijvingvolgnummer=volgnr, Bekostigingsindicatie=ind,
        CodeBekostigingstatus=code, Bekostigingsniveau="LAAG",
        Opleidingscode="34001", Opleidingsniveau="HBO-BA", Opleidingsfase="B",
        DatumInschrijving="20230901", DatumUitschrijving="20240831",
        EersteInschrijving="J", Inschrijvingsvorm="S", Onderwijsvorm="VT",
        DatumEersteAanlevering="20230915", Bekostigingsduur="12",
        OpleidingOnderdeel="TECHNIEK", Bekostigingscode="BEKOSTIGD",
        IndicatieSectorLG="N", IndicatieBaMa="B",
        IndicatieAcademischZiekenhuis="N",
        IndicatieNationaliteitsvoorwaardeSF="J", IndicatieGBARelatie="J",
    )


def analyse_regels(jaar: int = 2025, statussen: tuple[str, ...] | None = None) -> list[str]:
    """Mini-analysebestand: 2 personen, 3 BRD, 1 BRR, 1 BLB.

    Persoon 1 heeft BSN en onderwijsnummer; persoon 2 alleen een
    onderwijsnummer. ``statussen`` overschrijft de drie BRD-statuscodes.
    """
    s1, s2, s3 = statussen or ("pi", "mv", "na,ti")
    ind = {c: ("J" if c in {"pi", "pd"} else "N") for c in (s1, s2, s3)}
    return [
        maak_regel("analyse", "VLP", BRIN="99XX", Bekostigingsjaar=str(jaar),
                   DatumAanmaak=f"{jaar - 1}0115"),
        maak_regel("analyse", "BLB", Burgerservicenummer="700010001",
                   Onderwijsnummer="800010001", DatumGraadBehaaldBa="20230625",
                   VerbruikBA="1", AantalBekostigdeInschrijvingenBa="1",
                   AantalBekostigdeInschrijvingenMa="-1"),
        _brd("700010001", "800010001", "99XX", "INS001", ind[s1], s1),
        _brd("700010001", "800010001", "71AA", "EXT001", ind[s2], s2),
        maak_regel(
            "analyse", "BRR",
            Burgerservicenummer="700010001", Onderwijsnummer="800010001",
            BRIN="99XX", Resultaatvolgnummer="RES001", Bekostigingsindicatie="J",
            CodeBekostigingstatus="pg", Bekostigingsniveau="LAAG",
            JointDegreeFactor="1", Opleidingscode="34001",
            Opleidingsniveau="HBO-BA", Opleidingsfase="B", EersteGraad="J",
            DatumDiploma="20230625", Onderwijsvorm="VT",
            DatumEersteAanlevering="20230701", OpleidingOnderdeel="TECHNIEK",
            Bekostigingscode="BEKOSTIGD", IndicatieSectorLG="N",
            IndicatieBaMa="B", IndicatieAcademischZiekenhuis="N",
            IndicatieGraadTeltVoorBekostigingsloopbaan="J",
            IndicatieNationaliteitsvoorwaardeSF="J", IndicatieGBARelatie="J",
        ),
        _brd("", "800010002", "99XX", "INS002", ind[s3], s3),
        maak_regel("analyse", "SLR", AantalBLBrecords="1", AantalBRDrecords="3",
                   AantalBRRrecords="1"),
    ]


def hisbek_regels() -> list[str]:
    """Mini-HISBEK: 1 persoon, HRD voor 2023 en 2024, 1 HRR in 2024."""

    def hrd(jaar: str, code: str, ind: str) -> str:
        return maak_regel(
            "hisbek", "HRD",
            Burgerservicenummer="700010001", Onderwijsnummer="800010001",
            Bekostigingsjaar=jaar, BRIN="99XX", Inschrijvingvolgnummer="INS000",
            Bekostigingsindicatie=ind, CodeBekostigingstatus=code,
            Bekostigingsniveau="LAAG", Opleidingscode="34001",
            Opleidingsniveau="HBO-BA", Opleidingsfase="B",
            DatumInschrijving="20210901", DatumUitschrijving="20220831",
            EersteInschrijving="J", Inschrijvingsvorm="S", Onderwijsvorm="VT",
            DatumEersteAanlevering="20210915", ECTS="60.0", ECTSBekostigd="60.0",
            OpleidingOnderdeel="TECHNIEK", IndicatieNationaliteitsvoorwaardeSF="J",
            IndicatieGBARelatie="J",
        )

    return [
        maak_regel("hisbek", "VLP", BRIN="99XX", DatumAanmaak="20250301"),
        hrd("2023", "pi", "J"),
        hrd("2024", "ti", "N"),
        maak_regel(
            "hisbek", "HRR",
            Burgerservicenummer="700010001", Onderwijsnummer="800010001",
            Bekostigingsjaar="2024", BRIN="99XX", Resultaatvolgnummer="RES000",
            Bekostigingsindicatie="J", CodeBekostigingstatus="pg",
            JointDegreeFactor="1", Opleidingscode="34001",
            Opleidingsniveau="HBO-BA", Opleidingsfase="D", EersteGraad="N",
            DatumDiploma="20220625", Onderwijsvorm="VT",
            IndicatieGraadTeltVoorBekostigingsloopbaan="N",
            IndicatieNationaliteitsvoorwaardeSF="J",
        ),
        maak_regel("hisbek", "SLR", AantalHRDrecords="2", AantalHRRrecords="1"),
    ]


@pytest.fixture
def vlpbek_bestand(tmp_path: Path) -> Path:
    return schrijf_bestand(tmp_path, "VLPBEK_2025_20240115_99XX.csv", analyse_regels())


@pytest.fixture
def hisbek_bestand(tmp_path: Path) -> Path:
    return schrijf_bestand(tmp_path, "HISBEK_2024_20250301_99XX.csv", hisbek_regels())
```

- [ ] **Step 2: Schrijf de falende tests `tests/test_ingest.py`**

```python
from datetime import date

import pytest

from ho_bekostiging_bestanden.ingest import (
    MELDINGEN,
    Bestandsinfo,
    parse_bestandsnaam,
    read_multi_record_csv,
)
from ho_bekostiging_bestanden.metadata import load_schema

from .conftest import analyse_regels, schrijf_bestand


def test_parse_bestandsnaam_vlpbek():
    info = parse_bestandsnaam("data/VLPBEK_2025_20240115_99XX.csv")
    assert info == Bestandsinfo(
        soort="VLPBEK",
        bekostigingsjaar=2025,
        datum_aanmaak=date(2024, 1, 15),
        brin="99XX",
        bestandsnaam="VLPBEK_2025_20240115_99XX.csv",
    )


@pytest.mark.parametrize(
    "naam",
    [
        "defbek_2025_20240715_99xx.CSV",  # kleine letters, hoofdletter-extensie
        "DEFBEK_ 2025_20240715_99XX.CSV",  # spatie zoals in de PvE-notatie
    ],
)
def test_parse_bestandsnaam_varianten(naam):
    info = parse_bestandsnaam(naam)
    assert info is not None
    assert (info.soort, info.brin) == ("DEFBEK", "99XX")


@pytest.mark.parametrize(
    "naam",
    [
        "RO_27DV_20240731_20260324.csv",
        "VLPBEK_2025_20240115_99XX.txt",
        "VLPBEK_2025_20241340_99XX.csv",  # ongeldige datum
        "XYZBEK_2025_20240115_99XX.csv",
    ],
)
def test_parse_bestandsnaam_onbekend(naam):
    assert parse_bestandsnaam(naam) is None


def test_read_splitst_per_recordsoort(vlpbek_bestand):
    frames = read_multi_record_csv(vlpbek_bestand, "analyse")
    schema = load_schema("analyse")
    hoogtes = {rs: frames[rs].height for rs in ["VLP", "BLB", "BRD", "BRR", "SLR"]}
    assert hoogtes == {"VLP": 1, "BLB": 1, "BRD": 3, "BRR": 1, "SLR": 1}
    for rs in hoogtes:
        assert frames[rs].columns == schema[rs]["fields"]


def test_crlf_en_opvulling_verdwijnen(vlpbek_bestand):
    frames = read_multi_record_csv(vlpbek_bestand, "analyse")
    assert frames["SLR"]["AantalBRRrecords"][0] == "1"
    assert frames["BRD"]["IndicatieGBARelatie"].to_list() == ["J", "J", "J"]
    assert frames[MELDINGEN].height == 0


def test_onbekende_recordsoort_wordt_gemeld(tmp_path):
    regels = analyse_regels()
    regels.insert(2, "XYZ|iets")
    pad = schrijf_bestand(tmp_path, "VLPBEK_2025_20240115_99XX.csv", regels)
    meldingen = read_multi_record_csv(pad, "analyse")[MELDINGEN]
    assert meldingen.height == 1
    assert meldingen.row(0, named=True) == {
        "Regelnummer": 3,
        "Recordsoort": "XYZ",
        "Melding": "Onbekende recordsoort",
    }


def test_extra_gevulde_velden_worden_gemeld(tmp_path):
    regels = analyse_regels()
    regels[0] = regels[0] + "|extra"
    pad = schrijf_bestand(tmp_path, "VLPBEK_2025_20240115_99XX.csv", regels)
    meldingen = read_multi_record_csv(pad, "analyse")[MELDINGEN]
    assert meldingen["Recordsoort"].to_list() == ["VLP"]
    assert "meer gevulde velden" in meldingen["Melding"][0]


def test_latin1_bestand_is_leesbaar(tmp_path):
    pad = tmp_path / "VLPBEK_2025_20240115_99XX.csv"
    tekst = "\r\n".join(analyse_regels()).replace("INS002", "INSé02")
    pad.write_bytes(tekst.encode("latin-1"))
    frames = read_multi_record_csv(pad, "analyse")
    assert "INSé02" in frames["BRD"]["Inschrijvingvolgnummer"].to_list()


def test_leeg_bestand_geeft_fout(tmp_path):
    pad = tmp_path / "VLPBEK_2025_20240115_99XX.csv"
    pad.write_text("\r\n\r\n")
    with pytest.raises(ValueError, match="Leeg bestand"):
        read_multi_record_csv(pad, "analyse")


def test_ontbrekend_bestand_geeft_fout(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_multi_record_csv(tmp_path / "bestaat_niet.csv", "analyse")
```

Maak ook `tests/__init__.py` aan (leeg), zodat `from .conftest import …` werkt.

- [ ] **Step 3: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_ingest.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named 'ho_bekostiging_bestanden.ingest'`

- [ ] **Step 4: Schrijf `src/ho_bekostiging_bestanden/ingest.py`**

```python
"""Inlezen van ruwe HO-bekostigingsbestanden (analysebestand en HISBEK)."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import polars as pl

from ho_bekostiging_bestanden.metadata import load_schema

# Soort levering (eerste deel van de bestandsnaam) → schemanaam in metadata/.
SCHEMA_PER_LEVERING: dict[str, str] = {
    "VLPBEK": "analyse",
    "DEFBEK": "analyse",
    "HISBEK": "hisbek",
}

SEPARATOR = "|"
EXTENSIE = ".csv"

# Namen van de extra tabellen naast de recordsoorten. MELDINGEN vult ingest
# zelf; LEVERING en VALIDATIE vult de pipeline. Ze staan hier centraal zodat
# pipeline en star ze kunnen delen zonder circulaire import.
MELDINGEN = "_MELDINGEN"
LEVERING = "LEVERING"
VALIDATIE = "VALIDATIE"

# TTTTTT_JJJJ_EEJJMMDD_99XX — de PvE noteert "TTTTTT_ 1234", dus een spatie
# na de eerste underscore wordt getolereerd.
_BESTANDSNAAM_RE = re.compile(
    rf"^({'|'.join(SCHEMA_PER_LEVERING)})_ ?(\d{{4}})_(\d{{8}})_(\d{{2}}[A-Z]{{2}})$"
)

_MELDING_SCHEMA = {"Regelnummer": pl.Int64, "Recordsoort": pl.Utf8, "Melding": pl.Utf8}


@dataclass(frozen=True)
class Bestandsinfo:
    """Gegevens die uit de bestandsnaam van een levering af te leiden zijn."""

    soort: str
    bekostigingsjaar: int
    datum_aanmaak: date
    brin: str
    bestandsnaam: str


def parse_bestandsnaam(path: str | Path) -> Bestandsinfo | None:
    """Ontleed ``TTTTTT_JJJJ_EEJJMMDD_99XX.CSV``; ``None`` als het niet past.

    Hoofd- en kleine letters maken niet uit. Bij HISBEK is het jaar het
    laatste bekostigingsjaar in het bestand.
    """
    path = Path(path)
    if path.suffix.lower() != EXTENSIE:
        return None
    match = _BESTANDSNAAM_RE.match(path.stem.upper())
    if match is None:
        return None
    soort, jaar, datum, brin = match.groups()
    try:
        datum_aanmaak = datetime.strptime(datum, "%Y%m%d").date()
    except ValueError:
        return None
    return Bestandsinfo(soort, int(jaar), datum_aanmaak, brin, path.name)


def _lees_regels(path: Path) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")
    return content.splitlines()


def read_multi_record_csv(
    path: str | Path,
    schema_name: str,
) -> dict[str, pl.DataFrame]:
    """Lees een multi-record ``|``-bestand in en splits per recordsoort.

    Elke regel wordt afgekapt of aangevuld tot het aantal velden in het
    schema; DUO vult regels op met lege velden. Afwijkingen (onbekende
    recordsoort, gevulde velden voorbij het schema) komen in het frame
    ``MELDINGEN``.

    Args:
        path:        Pad naar het bronbestand.
        schema_name: Naam van het schema (``"analyse"`` of ``"hisbek"``).

    Returns:
        Dict van recordsoort naar DataFrame (alle kolommen tekst) plus
        ``MELDINGEN``. Recordsoorten zonder regels ontbreken.

    Raises:
        FileNotFoundError: Als het bronbestand of het schema niet bestaat.
        ValueError:        Als het bestand leeg is.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Bronbestand niet gevonden: {path}")

    schema = {rs: spec["fields"] for rs, spec in load_schema(schema_name).items()}
    regels = _lees_regels(path)
    if not any(r.strip() for r in regels):
        raise ValueError(f"Leeg bestand: {path}")

    rijen: dict[str, list[list[str]]] = {rs: [] for rs in schema}
    meldingen: list[dict] = []
    for regelnummer, regel in enumerate(regels, start=1):
        if not regel.strip():
            continue
        velden = regel.split(SEPARATOR)
        rs = velden[0]
        if rs not in schema:
            meldingen.append(
                {"Regelnummer": regelnummer, "Recordsoort": rs,
                 "Melding": "Onbekende recordsoort"}
            )
            continue
        n = len(schema[rs])
        extra = [v for v in velden[n:] if v.strip()]
        if extra:
            meldingen.append(
                {"Regelnummer": regelnummer, "Recordsoort": rs,
                 "Melding": f"{len(extra)} meer gevulde velden dan het schema ({n})"}
            )
        rijen[rs].append((velden + [""] * n)[:n])

    result = {
        rs: pl.DataFrame(
            {col: [r[i] for r in rs_rijen] for i, col in enumerate(schema[rs])},
            schema={col: pl.Utf8 for col in schema[rs]},
        )
        for rs, rs_rijen in rijen.items()
        if rs_rijen
    }
    result[MELDINGEN] = pl.DataFrame(meldingen, schema=_MELDING_SCHEMA)
    return result
```

- [ ] **Step 5: Run de tests**

Run: `uv run pytest tests/test_ingest.py -v`
Expected: alle tests PASS.

- [ ] **Step 6: Lint en commit**

```bash
uv run ruff format . && uv run ruff check .
git add src/ho_bekostiging_bestanden/ingest.py tests/
git commit -m "feat(ingest): bestandsnaam ontleden en multi-record inlezen met meldingen

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Decode — typen omzetten volgens het schema

**Files:**
- Create: `src/ho_bekostiging_bestanden/decode.py`
- Test: `tests/test_decode.py`

**Interfaces:**
- Consumes: `read_multi_record_csv`, `MELDINGEN` (Task 3), `load_schema` (Task 2).
- Produces: `decode_frames(frames: dict[str, pl.DataFrame], schema_name: str) -> dict[str, pl.DataFrame]`. Na decode geldt:
  - lege tekst wordt `null` (alle tekstkolommen, ook na strippen van spaties);
  - `date_fields` zijn `pl.Date`; bij een ongeldige, niet-lege waarde is de datum `null` en staat de ruwe waarde in `<Veld>_Ruw`. Die kolom bestaat alleen als er minstens één ongeldige waarde is;
  - `bool_fields` zijn `pl.Boolean` (`J` → True, `N` → False, anders null);
  - `int_fields` zijn `pl.Int64`; `float_fields` zijn `pl.Float64` (komma of punt als decimaalteken);
  - `nvt_fields`: `-1` wordt `null`, met een extra kolom `<Veld>_NVT: Boolean` (True bij `-1`);
  - `CodeBekostigingstatus` blijft tekst: kleine letters, zonder spaties, codes gesorteerd (`" TI, na"` → `"na,ti"`);
  - `MELDINGEN` en recordsoorten die niet in het schema staan, blijven onveranderd.

- [ ] **Step 1: Schrijf de falende tests `tests/test_decode.py`**

```python
from datetime import date

import polars as pl

from ho_bekostiging_bestanden.decode import decode_frames
from ho_bekostiging_bestanden.ingest import MELDINGEN, read_multi_record_csv

from .conftest import analyse_regels, maak_regel, schrijf_bestand


def _decode(tmp_path, regels, schema="analyse"):
    pad = schrijf_bestand(tmp_path, "VLPBEK_2025_20240115_99XX.csv", regels)
    return decode_frames(read_multi_record_csv(pad, schema), schema)


def test_datums_en_booleans(vlpbek_bestand):
    frames = decode_frames(read_multi_record_csv(vlpbek_bestand, "analyse"), "analyse")
    brd = frames["BRD"]
    assert brd.schema["DatumInschrijving"] == pl.Date
    assert brd["DatumInschrijving"][0] == date(2023, 9, 1)
    assert brd.schema["Bekostigingsindicatie"] == pl.Boolean
    assert brd["Bekostigingsindicatie"].to_list() == [True, False, False]
    assert frames["VLP"]["Bekostigingsjaar"][0] == 2025
    assert frames["BRR"]["JointDegreeFactor"][0] == 1.0


def test_lege_tekst_wordt_null(vlpbek_bestand):
    frames = decode_frames(read_multi_record_csv(vlpbek_bestand, "analyse"), "analyse")
    assert frames["BRD"]["Burgerservicenummer"].to_list()[-1] is None
    assert "_Ruw" not in "".join(frames["BRD"].columns)


def test_ongeldige_datum_bewaart_ruwe_waarde(tmp_path):
    regels = analyse_regels()
    regels[1] = maak_regel(
        "analyse", "BLB", Burgerservicenummer="700010001",
        DatumGraadBehaaldBa="20230000",
    )
    blb = _decode(tmp_path, regels)["BLB"]
    assert blb["DatumGraadBehaaldBa"][0] is None
    assert blb["DatumGraadBehaaldBa_Ruw"][0] == "20230000"


def test_min_een_wordt_nvt(vlpbek_bestand):
    blb = decode_frames(read_multi_record_csv(vlpbek_bestand, "analyse"), "analyse")["BLB"]
    assert blb["AantalBekostigdeInschrijvingenMa"][0] is None
    assert blb["AantalBekostigdeInschrijvingenMa_NVT"][0] is True
    assert blb["AantalBekostigdeInschrijvingenBa"][0] == 1
    assert blb["AantalBekostigdeInschrijvingenBa_NVT"][0] is False


def test_statuscode_wordt_genormaliseerd(tmp_path):
    brd = _decode(tmp_path, analyse_regels(statussen=("pi", "mv", " TI, na")))["BRD"]
    assert brd["CodeBekostigingstatus"].to_list() == ["pi", "mv", "na,ti"]


def test_hisbek_float_met_komma(tmp_path):
    from .conftest import hisbek_regels

    regels = [r.replace("60.0", "60,5") for r in hisbek_regels()]
    hrd = _decode(tmp_path, regels, schema="hisbek")["HRD"]
    assert hrd["ECTS"].to_list() == [60.5, 60.5]
    assert hrd.schema["Bekostigingsjaar"] == pl.Int64


def test_meldingen_blijven_ongewijzigd(tmp_path):
    regels = analyse_regels()
    regels.insert(1, "XYZ|x")
    frames = _decode(tmp_path, regels)
    assert frames[MELDINGEN].height == 1
```

- [ ] **Step 2: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_decode.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named 'ho_bekostiging_bestanden.decode'`

- [ ] **Step 3: Schrijf `src/ho_bekostiging_bestanden/decode.py`**

```python
"""Decoderen: tekstvelden omzetten naar de juiste typen via de schema-TOML."""

import polars as pl

from ho_bekostiging_bestanden.metadata import load_schema

DATUM_FORMAAT = "%Y%m%d"
WAAR = "J"
ONWAAR = "N"
NVT_WAARDE = "-1"
STATUS_VELD = "CodeBekostigingstatus"
STATUS_SCHEIDING = ","
RUW_SUFFIX = "_Ruw"
NVT_SUFFIX = "_NVT"


def _normaliseer_status(kolom: str) -> pl.Expr:
    """Kleine letters, geen spaties, codes gesorteerd: ``" TI, na"`` → ``"na,ti"``."""
    return (
        pl.col(kolom)
        .str.to_lowercase()
        .str.replace_all(r"\s", "")
        .str.split(STATUS_SCHEIDING)
        .list.eval(pl.element().filter(pl.element() != ""))
        .list.sort()
        .list.join(STATUS_SCHEIDING)
        .replace("", None)
        .alias(kolom)
    )


def _leeg_naar_null(df: pl.DataFrame) -> pl.DataFrame:
    tekst = [c for c, t in df.schema.items() if t == pl.Utf8]
    return df.with_columns(
        pl.col(c).str.strip_chars().replace("", None).alias(c) for c in tekst
    )


def _decode_datums(df: pl.DataFrame, velden: list[str]) -> pl.DataFrame:
    for veld in velden:
        geparsed = pl.col(veld).str.to_date(DATUM_FORMAAT, strict=False)
        ongeldig = pl.col(veld).is_not_null() & geparsed.is_null()
        if df.select(ongeldig.any()).item():
            df = df.with_columns(
                pl.when(ongeldig).then(pl.col(veld)).alias(f"{veld}{RUW_SUFFIX}")
            )
        df = df.with_columns(geparsed.alias(veld))
    return df


def _decode_booleans(df: pl.DataFrame, velden: list[str]) -> pl.DataFrame:
    return df.with_columns(
        pl.when(pl.col(v) == WAAR)
        .then(True)
        .when(pl.col(v) == ONWAAR)
        .then(False)
        .otherwise(None)
        .cast(pl.Boolean)
        .alias(v)
        for v in velden
    )


def _decode_nvt(df: pl.DataFrame, velden: list[str]) -> pl.DataFrame:
    return df.with_columns(
        *[(pl.col(v) == NVT_WAARDE).fill_null(False).alias(f"{v}{NVT_SUFFIX}")
          for v in velden],
        *[pl.col(v).replace(NVT_WAARDE, None).alias(v) for v in velden],
    )


def _decode_getallen(
    df: pl.DataFrame, int_velden: list[str], float_velden: list[str]
) -> pl.DataFrame:
    return df.with_columns(
        *[pl.col(v).cast(pl.Int64, strict=False).alias(v) for v in int_velden],
        *[
            pl.col(v).str.replace(",", ".").cast(pl.Float64, strict=False).alias(v)
            for v in float_velden
        ],
    )


def _decode_recordsoort(df: pl.DataFrame, spec: dict) -> pl.DataFrame:
    df = _leeg_naar_null(df)
    if STATUS_VELD in df.columns:
        df = df.with_columns(_normaliseer_status(STATUS_VELD))
    df = _decode_datums(df, spec.get("date_fields", []))
    df = _decode_booleans(df, spec.get("bool_fields", []))
    df = _decode_nvt(df, spec.get("nvt_fields", []))
    return _decode_getallen(df, spec.get("int_fields", []), spec.get("float_fields", []))


def decode_frames(
    frames: dict[str, pl.DataFrame],
    schema_name: str,
) -> dict[str, pl.DataFrame]:
    """Zet de tekstkolommen per recordsoort om naar de typen uit het schema.

    Args:
        frames:      Uitvoer van :func:`read_multi_record_csv`.
        schema_name: ``"analyse"`` of ``"hisbek"``.

    Returns:
        Nieuwe dict met getypeerde DataFrames; frames die niet in het schema
        staan (zoals ``MELDINGEN``) blijven onveranderd.
    """
    schema = load_schema(schema_name)
    return {
        rs: _decode_recordsoort(df, schema[rs]) if rs in schema else df
        for rs, df in frames.items()
    }
```

- [ ] **Step 4: Run de tests**

Run: `uv run pytest tests/test_decode.py -v`
Expected: alle tests PASS.

- [ ] **Step 5: Lint en commit**

```bash
uv run ruff format . && uv run ruff check .
git add src/ho_bekostiging_bestanden/decode.py tests/test_decode.py
git commit -m "feat(decode): datums, J/N, getallen, n.v.t. en statuscodes normaliseren

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Validate en export

**Files:**
- Create: `src/ho_bekostiging_bestanden/validate.py`
- Create: `src/ho_bekostiging_bestanden/export.py`
- Test: `tests/test_validate.py`, `tests/test_export.py`

**Interfaces:**
- Consumes: `Bestandsinfo`, `MELDINGEN`, `read_multi_record_csv`, `parse_bestandsnaam` (Task 3); `decode_frames` (Task 4); `load_schema`, `load_codelijst` (Task 2).
- Produces:
  - `validate.VALIDATIE_SCHEMA: dict[str, pl.DataType]` = `{"Controle": Utf8, "Recordsoort": Utf8, "Melding": Utf8, "Aantal": Int64}`
  - `validate.valideer(frames: dict[str, pl.DataFrame], schema_name: str, info: Bestandsinfo) -> pl.DataFrame`: geeft de meldingen terug (leeg frame = alles goed) en gooit alleen `ValueError` als er geen VLP-record is. Controles: `Inlezen`, `Aantal records`, `Eén rij`, `Verplicht veld`, `Codelijst`, `Bestandsnaam`.
  - `export.OutputFormat = Literal["parquet", "csv"]`
  - `export.export_frames(frames, output_dir, fmt="parquet") -> list[Path]`: één bestand per sleutel (`<sleutel>.<fmt>`).

- [ ] **Step 1: Schrijf de falende tests `tests/test_validate.py`**

```python
import pytest

from ho_bekostiging_bestanden.decode import decode_frames
from ho_bekostiging_bestanden.ingest import parse_bestandsnaam, read_multi_record_csv
from ho_bekostiging_bestanden.validate import VALIDATIE_SCHEMA, valideer

from .conftest import analyse_regels, maak_regel, schrijf_bestand

NAAM = "VLPBEK_2025_20240115_99XX.csv"


def _valideer(tmp_path, regels, naam=NAAM):
    pad = schrijf_bestand(tmp_path, naam, regels)
    frames = decode_frames(read_multi_record_csv(pad, "analyse"), "analyse")
    return valideer(frames, "analyse", parse_bestandsnaam(pad))


def test_schoon_bestand_geeft_geen_meldingen(tmp_path):
    rapport = _valideer(tmp_path, analyse_regels())
    assert rapport.schema == VALIDATIE_SCHEMA
    assert rapport.height == 0


def test_hisbek_schoon(hisbek_bestand):
    frames = decode_frames(read_multi_record_csv(hisbek_bestand, "hisbek"), "hisbek")
    rapport = valideer(frames, "hisbek", parse_bestandsnaam(hisbek_bestand))
    assert rapport.height == 0


def test_slr_telling_klopt_niet(tmp_path):
    regels = analyse_regels()
    regels[-1] = maak_regel("analyse", "SLR", AantalBLBrecords="1",
                            AantalBRDrecords="4", AantalBRRrecords="1")
    rapport = _valideer(tmp_path, regels)
    rij = rapport.row(0, named=True)
    assert (rij["Controle"], rij["Recordsoort"]) == ("Aantal records", "BRD")
    assert rij["Melding"] == "SLR meldt 4, gevonden 3"


def test_verplicht_veld_leeg(tmp_path):
    regels = analyse_regels()
    regels[2] = regels[2].replace("|34001|", "||", 1)
    rapport = _valideer(tmp_path, regels)
    rij = rapport.filter(rapport["Controle"] == "Verplicht veld").row(0, named=True)
    assert rij["Melding"] == "Opleidingscode is leeg"
    assert rij["Aantal"] == 1


def test_onbekende_code(tmp_path):
    rapport = _valideer(tmp_path, analyse_regels(statussen=("pi", "zz", "na,qq")))
    codes = rapport.filter(rapport["Controle"] == "Codelijst")["Melding"].to_list()
    assert sorted(codes) == [
        "CodeBekostigingstatus: onbekende code 'qq'",
        "CodeBekostigingstatus: onbekende code 'zz'",
    ]


def test_brin_in_naam_wijkt_af(tmp_path):
    rapport = _valideer(tmp_path, analyse_regels(), naam="VLPBEK_2025_20240115_00AA.csv")
    assert rapport["Controle"].to_list() == ["Bestandsnaam"]
    assert "00AA" in rapport["Melding"][0]


def test_meldingen_uit_ingest_komen_mee(tmp_path):
    regels = analyse_regels()
    regels.insert(1, "XYZ|x")
    regels.insert(2, "XYZ|y")
    rapport = _valideer(tmp_path, regels)
    rij = rapport.row(0, named=True)
    assert (rij["Controle"], rij["Recordsoort"], rij["Aantal"]) == ("Inlezen", "XYZ", 2)


def test_zonder_vlp_is_fout(tmp_path):
    with pytest.raises(ValueError, match="VLP"):
        _valideer(tmp_path, analyse_regels()[1:])
```

- [ ] **Step 2: Schrijf de falende tests `tests/test_export.py`**

```python
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
        export_frames({}, tmp_path, fmt="xlsx")  # type: ignore[arg-type]
```

- [ ] **Step 3: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_validate.py tests/test_export.py -v`
Expected: FAIL met `ModuleNotFoundError` voor `validate` en `export`.

- [ ] **Step 4: Schrijf `src/ho_bekostiging_bestanden/validate.py`**

```python
"""Kwaliteitscontroles op een ingelezen levering.

De controles houden de verwerking niet tegen: ze leveren een rapport op dat
in de app en in de tabel ``VALIDATIE`` getoond wordt. Alleen een ontbrekend
voorlooprecord is fataal, omdat de levering dan niet te plaatsen is.
"""

import re

import polars as pl

from ho_bekostiging_bestanden.decode import STATUS_SCHEIDING
from ho_bekostiging_bestanden.ingest import MELDINGEN, Bestandsinfo
from ho_bekostiging_bestanden.metadata import load_codelijst, load_schema

VALIDATIE_SCHEMA = {
    "Controle": pl.Utf8,
    "Recordsoort": pl.Utf8,
    "Melding": pl.Utf8,
    "Aantal": pl.Int64,
}
VOORLOOP = "VLP"
SLUIT = "SLR"
_SLR_VELD_RE = re.compile(r"^Aantal([A-Z]{3})records$")


def _melding(controle: str, rs: str, melding: str, aantal: int = 1) -> dict:
    return {"Controle": controle, "Recordsoort": rs, "Melding": melding, "Aantal": aantal}


def _inlezen(frames: dict[str, pl.DataFrame]) -> list[dict]:
    meldingen = frames.get(MELDINGEN)
    if meldingen is None or meldingen.is_empty():
        return []
    telling = meldingen.group_by(["Recordsoort", "Melding"], maintain_order=True).len()
    return [
        _melding("Inlezen", r["Recordsoort"], r["Melding"], r["len"])
        for r in telling.iter_rows(named=True)
    ]


def _aantal_records(frames: dict[str, pl.DataFrame]) -> list[dict]:
    slr = frames.get(SLUIT)
    if slr is None or slr.is_empty():
        return [_melding("Aantal records", SLUIT, "Geen sluitrecord (SLR)")]
    uitkomst = []
    for veld in slr.columns:
        match = _SLR_VELD_RE.match(veld)
        if match is None:
            continue
        rs = match.group(1)
        verwacht = slr[veld][0]
        gevonden = frames[rs].height if rs in frames else 0
        if verwacht != gevonden:
            uitkomst.append(
                _melding("Aantal records", rs, f"SLR meldt {verwacht}, gevonden {gevonden}")
            )
    return uitkomst


def _een_rij(frames: dict[str, pl.DataFrame], schema: dict[str, dict]) -> list[dict]:
    return [
        _melding("Eén rij", rs, f"Verwacht 1 rij, gevonden {frames[rs].height}")
        for rs, spec in schema.items()
        if spec.get("single_row") and rs in frames and frames[rs].height != 1
    ]


def _verplicht(frames: dict[str, pl.DataFrame], schema: dict[str, dict]) -> list[dict]:
    uitkomst = []
    for rs, spec in schema.items():
        if rs not in frames:
            continue
        for veld in spec.get("required_fields", []):
            leeg = frames[rs][veld].null_count()
            if leeg:
                uitkomst.append(_melding("Verplicht veld", rs, f"{veld} is leeg", leeg))
    return uitkomst


def _codelijsten(frames: dict[str, pl.DataFrame], schema: dict[str, dict]) -> list[dict]:
    uitkomst = []
    for rs, spec in schema.items():
        if rs not in frames:
            continue
        for veld, lijst in spec.get("codelijsten", {}).items():
            geldig = load_codelijst(lijst)["Code"].to_list()
            onbekend = (
                frames[rs]
                .select(pl.col(veld).str.split(STATUS_SCHEIDING).explode().alias("c"))
                .drop_nulls()
                .filter(~pl.col("c").is_in(geldig))
                .group_by("c", maintain_order=True)
                .len()
                .sort("c")
            )
            uitkomst += [
                _melding("Codelijst", rs, f"{veld}: onbekende code '{r['c']}'", r["len"])
                for r in onbekend.iter_rows(named=True)
            ]
    return uitkomst


def _bestandsnaam(vlp: pl.DataFrame, info: Bestandsinfo) -> list[dict]:
    uitkomst = []
    brin = vlp["BRIN"][0]
    if brin != info.brin:
        uitkomst.append(_melding(
            "Bestandsnaam", VOORLOOP,
            f"BRIN in bestandsnaam ({info.brin}) wijkt af van VLP ({brin})",
        ))
    if "Bekostigingsjaar" in vlp.columns:
        jaar = vlp["Bekostigingsjaar"][0]
        if jaar != info.bekostigingsjaar:
            uitkomst.append(_melding(
                "Bestandsnaam", VOORLOOP,
                f"Jaar in bestandsnaam ({info.bekostigingsjaar}) wijkt af van VLP ({jaar})",
            ))
    return uitkomst


def valideer(
    frames: dict[str, pl.DataFrame],
    schema_name: str,
    info: Bestandsinfo,
) -> pl.DataFrame:
    """Controleer een gedecodeerde levering en geef de meldingen terug.

    Args:
        frames:      Uitvoer van :func:`decode_frames` (inclusief ``MELDINGEN``).
        schema_name: ``"analyse"`` of ``"hisbek"``.
        info:        Gegevens uit de bestandsnaam.

    Returns:
        DataFrame met kolommen ``VALIDATIE_SCHEMA``; leeg als alles klopt.

    Raises:
        ValueError: Als het voorlooprecord (VLP) ontbreekt.
    """
    if VOORLOOP not in frames or frames[VOORLOOP].is_empty():
        raise ValueError(f"Geen voorlooprecord (VLP) in {info.bestandsnaam}")
    schema = load_schema(schema_name)
    rijen = (
        _inlezen(frames)
        + _aantal_records(frames)
        + _een_rij(frames, schema)
        + _verplicht(frames, schema)
        + _codelijsten(frames, schema)
        + _bestandsnaam(frames[VOORLOOP], info)
    )
    return pl.DataFrame(rijen, schema=VALIDATIE_SCHEMA)
```

- [ ] **Step 5: Schrijf `src/ho_bekostiging_bestanden/export.py`**

```python
"""Wegschrijven van schone data naar de output-map."""

from pathlib import Path
from typing import Literal

import polars as pl

OutputFormat = Literal["parquet", "csv"]
_FORMATEN = ("parquet", "csv")


def export_frames(
    frames: dict[str, pl.DataFrame],
    output_dir: str | Path,
    fmt: OutputFormat = "parquet",
) -> list[Path]:
    """Schrijf elke tabel als apart bestand naar ``output_dir``.

    Args:
        frames:     Dict van tabelnaam naar DataFrame.
        output_dir: Doelmap (wordt aangemaakt als die niet bestaat).
        fmt:        ``"parquet"`` (standaard) of ``"csv"``.

    Returns:
        Lijst van geschreven paden.

    Raises:
        ValueError: Als ``fmt`` geen ondersteund formaat is.
    """
    if fmt not in _FORMATEN:
        raise ValueError(f"Onbekend formaat {fmt!r}. Kies uit {_FORMATEN}.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for naam, df in frames.items():
        path = output_dir / f"{naam}.{fmt}"
        if fmt == "parquet":
            df.write_parquet(path)
        else:
            df.write_csv(path)
        written.append(path)
    return written
```

- [ ] **Step 6: Run de tests**

Run: `uv run pytest tests/test_validate.py tests/test_export.py -v`
Expected: alle tests PASS.

- [ ] **Step 7: Lint en commit**

```bash
uv run ruff format . && uv run ruff check .
git add src/ho_bekostiging_bestanden/validate.py src/ho_bekostiging_bestanden/export.py tests/test_validate.py tests/test_export.py
git commit -m "feat(validate,export): niet-blokkerend validatierapport en Parquet/CSV-export

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Pipeline en CLI `ho verwerk`

**Files:**
- Create: `src/ho_bekostiging_bestanden/pipeline.py`
- Create: `src/ho_bekostiging_bestanden/cli.py`
- Test: `tests/test_pipeline.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces:
  - `pipeline` exporteert `LEVERING` en `VALIDATIE` opnieuw (gedefinieerd in `ingest.py`, Task 3)
  - `pipeline.detect_levering(path) -> str | None`: `"VLPBEK"`, `"DEFBEK"`, `"HISBEK"` of `None`.
  - `pipeline.run_pipeline(source, target, fmt="parquet") -> dict[str, pl.DataFrame]`: schrijft de recordsoorten plus `LEVERING` en `VALIDATIE` naar `target` (zonder `_MELDINGEN`) en geeft dezelfde dict terug. Een onbekende bestandsnaam geeft `ValueError("Onbekend bestandstype: …")`.
  - Tabel `LEVERING` (één rij): `SoortLevering: Utf8`, `Bekostigingsjaar: Int64` (uit de bestandsnaam), `DatumAanmaak: Date` (uit de VLP), `BrinOntvanger: Utf8` (uit de VLP), `Bestandsnaam: Utf8`, `SchemaVersie: Utf8`.
  - `cli.build_parser() -> argparse.ArgumentParser`, `cli.main() -> None`; subcommando `verwerk <source> <target> [--fmt parquet|csv]`.

- [ ] **Step 1: Schrijf de falende tests `tests/test_pipeline.py`**

```python
from datetime import date

import polars as pl
import pytest

from ho_bekostiging_bestanden.pipeline import (
    LEVERING,
    VALIDATIE,
    detect_levering,
    run_pipeline,
)


def test_detect_levering():
    assert detect_levering("x/DEFBEK_2025_20240715_99XX.CSV") == "DEFBEK"
    assert detect_levering("x/RO_27DV_20240731_20260324.csv") is None


def test_run_pipeline_vlpbek(tmp_path, vlpbek_bestand):
    doel = tmp_path / "prep"
    frames = run_pipeline(vlpbek_bestand, doel)
    geschreven = {p.stem for p in doel.glob("*.parquet")}
    assert geschreven == {"VLP", "BLB", "BRD", "BRR", "SLR", LEVERING, VALIDATIE}
    assert "_MELDINGEN" not in frames
    levering = pl.read_parquet(doel / f"{LEVERING}.parquet").row(0, named=True)
    assert levering == {
        "SoortLevering": "VLPBEK",
        "Bekostigingsjaar": 2025,
        "DatumAanmaak": date(2024, 1, 15),
        "BrinOntvanger": "99XX",
        "Bestandsnaam": "VLPBEK_2025_20240115_99XX.csv",
        "SchemaVersie": "26.3.1",
    }
    assert frames[VALIDATIE].height == 0


def test_run_pipeline_hisbek(tmp_path, hisbek_bestand):
    frames = run_pipeline(hisbek_bestand, tmp_path / "prep")
    assert frames[LEVERING]["Bekostigingsjaar"][0] == 2024
    assert frames["HRD"].height == 2


def test_run_pipeline_csv(tmp_path, vlpbek_bestand):
    run_pipeline(vlpbek_bestand, tmp_path / "prep", fmt="csv")
    assert pl.read_csv(tmp_path / "prep" / "BRD.csv").height == 3


def test_onbekend_bestand(tmp_path):
    pad = tmp_path / "RO_27DV_20240731_20260324.csv"
    pad.write_text("VLP|x")
    with pytest.raises(ValueError, match="Onbekend bestandstype"):
        run_pipeline(pad, tmp_path / "prep")
```

- [ ] **Step 2: Schrijf de falende test `tests/test_cli.py`**

```python
import sys

from ho_bekostiging_bestanden.cli import main


def test_cli_verwerk(tmp_path, vlpbek_bestand, monkeypatch, capsys):
    doel = tmp_path / "prep"
    monkeypatch.setattr(sys, "argv", ["ho", "verwerk", str(vlpbek_bestand), str(doel)])
    main()
    assert "Verwerkt:" in capsys.readouterr().out
    assert (doel / "BRD.parquet").exists()
```

- [ ] **Step 3: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_pipeline.py tests/test_cli.py -v`
Expected: FAIL met `ModuleNotFoundError` voor `pipeline` en `cli`.

- [ ] **Step 4: Schrijf `src/ho_bekostiging_bestanden/pipeline.py`**

```python
"""Orkestratie van de ingestion-pipeline: ingest > decode > validate > export."""

from pathlib import Path

import polars as pl

from ho_bekostiging_bestanden.decode import decode_frames
from ho_bekostiging_bestanden.export import OutputFormat, export_frames
from ho_bekostiging_bestanden.ingest import (
    LEVERING,
    MELDINGEN,
    SCHEMA_PER_LEVERING,
    VALIDATIE,
    Bestandsinfo,
    parse_bestandsnaam,
    read_multi_record_csv,
)
from ho_bekostiging_bestanden.metadata import schema_meta
from ho_bekostiging_bestanden.validate import VOORLOOP, valideer

__all__ = ["LEVERING", "VALIDATIE", "detect_levering", "run_pipeline"]


def detect_levering(path: str | Path) -> str | None:
    """Geef de soort levering (``VLPBEK``/``DEFBEK``/``HISBEK``) of ``None``."""
    info = parse_bestandsnaam(path)
    return info.soort if info else None


def _levering_tabel(info: Bestandsinfo, vlp: pl.DataFrame, schema_name: str) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "SoortLevering": [info.soort],
            "Bekostigingsjaar": [info.bekostigingsjaar],
            "DatumAanmaak": [vlp["DatumAanmaak"][0]],
            "BrinOntvanger": [vlp["BRIN"][0]],
            "Bestandsnaam": [info.bestandsnaam],
            "SchemaVersie": [str(schema_meta(schema_name)["schema_version"])],
        },
        schema={
            "SoortLevering": pl.Utf8,
            "Bekostigingsjaar": pl.Int64,
            "DatumAanmaak": pl.Date,
            "BrinOntvanger": pl.Utf8,
            "Bestandsnaam": pl.Utf8,
            "SchemaVersie": pl.Utf8,
        },
    )


def run_pipeline(
    source: str | Path,
    target: str | Path,
    fmt: OutputFormat = "parquet",
) -> dict[str, pl.DataFrame]:
    """Verwerk één ruw analysebestand of HISBEK-bestand naar ``target``.

    Args:
        source: Pad naar het ruwe bestand (``VLPBEK_…``, ``DEFBEK_…``, ``HISBEK_…``).
        target: Doelmap voor de prepared-tabellen.
        fmt:    ``"parquet"`` (standaard) of ``"csv"``.

    Returns:
        Dict van tabelnaam naar DataFrame: de recordsoorten plus ``LEVERING``
        en ``VALIDATIE``.

    Raises:
        ValueError: Als de bestandsnaam niet herkend wordt of de VLP ontbreekt.
    """
    info = parse_bestandsnaam(source)
    if info is None:
        raise ValueError(
            f"Onbekend bestandstype: {Path(source).name!r}. "
            f"Verwacht TTTTTT_JJJJ_EEJJMMDD_99XX.csv met TTTTTT in "
            f"{sorted(SCHEMA_PER_LEVERING)}."
        )
    schema_name = SCHEMA_PER_LEVERING[info.soort]
    frames = decode_frames(read_multi_record_csv(source, schema_name), schema_name)
    rapport = valideer(frames, schema_name, info)
    uitvoer = {rs: df for rs, df in frames.items() if rs != MELDINGEN}
    uitvoer[LEVERING] = _levering_tabel(info, frames[VOORLOOP], schema_name)
    uitvoer[VALIDATIE] = rapport
    export_frames(uitvoer, target, fmt=fmt)
    return uitvoer
```

- [ ] **Step 5: Schrijf `src/ho_bekostiging_bestanden/cli.py`**

```python
"""CLI voor de HO-bekostigingsbestanden pipeline.

Gebruik:
    ho verwerk <source> <target> [--fmt parquet|csv]
"""

import argparse
from pathlib import Path

from ho_bekostiging_bestanden.pipeline import run_pipeline


def _verwerk(args: argparse.Namespace) -> None:
    frames = run_pipeline(args.source, args.target, fmt=args.fmt)
    total = sum(df.height for df in frames.values())
    print(f"Verwerkt: {len(frames)} tabellen, {total} rijen → {args.target}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ho",
        description="HO-bekostigingsbestanden pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_verwerk = sub.add_parser("verwerk", help="Verwerk één ruw bestand")
    p_verwerk.add_argument("source", type=Path, help="Pad naar het ruwe bronbestand")
    p_verwerk.add_argument("target", type=Path, help="Doelmap voor de uitvoer")
    p_verwerk.add_argument(
        "--fmt",
        default="parquet",
        choices=["parquet", "csv"],
        help="Uitvoerformaat (standaard: parquet)",
    )
    p_verwerk.set_defaults(func=_verwerk)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)
```

- [ ] **Step 6: Run de tests**

Run: `uv run pytest tests/test_pipeline.py tests/test_cli.py -v`
Expected: alle tests PASS.

- [ ] **Step 7: Lint en commit**

```bash
uv run ruff format . && uv run ruff check .
git add src/ho_bekostiging_bestanden/pipeline.py src/ho_bekostiging_bestanden/cli.py tests/test_pipeline.py tests/test_cli.py
git commit -m "feat(pipeline,cli): ho verwerk met LEVERING- en VALIDATIE-tabel

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Stack en star schema

**Files:**
- Create: `src/ho_bekostiging_bestanden/stack.py`
- Create: `src/ho_bekostiging_bestanden/star.py`
- Test: `tests/test_stack.py`, `tests/test_star.py`

**Interfaces:**
- Consumes: `run_pipeline`, `LEVERING` (Task 6); `load_schema`, `load_codelijst` (Task 2); `SCHEMA_PER_LEVERING` (Task 3); `STATUS_SCHEIDING` (Task 4).
- Produces:
  - `stack.LABEL_COL = "levering"`
  - `stack.stack_prepared(sources: Sequence[Path | str], label_col: str = LABEL_COL, labels: list[str] | None = None) -> dict[str, pl.DataFrame]`: leest `*.parquet` per map, voegt `levering` (standaard de mapnaam) als eerste kolom toe en voegt tabellen met dezelfde naam samen (`diagonal_relaxed`).
  - `star.STAR_TABELLEN: tuple[str, ...]` = `("dim_levering", "dim_persoon", "dim_instelling", "dim_opleiding", "dim_status", "fact_deelname", "fact_resultaat", "fact_status", "fact_loopbaan")`
  - `star.PERSOON_ID = "_persoon_id"`, `star.FEIT_ID = "_feit_id"`
  - `star.build_star(stacked: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]`: geeft altijd alle 9 tabellen terug, ook als de invoer leeg is (dan met 0 rijen en vaste kolommen).
  - Kolommen die later gebruikt worden:
    - `dim_levering`: `levering, SoortLevering, Bekostigingsjaar, DatumAanmaak, BrinOntvanger, Bestandsnaam`
    - `dim_persoon`: `_persoon_id, Burgerservicenummer, Onderwijsnummer, DatumGraadBehaaldAD … DatumGraadBehaaldMaLG`
    - `dim_instelling`: `BRIN, EigenInstelling (Boolean)`
    - `dim_opleiding`: `Opleidingscode, Opleidingsniveau, OpleidingOnderdeel, IndicatieSectorLG, IndicatieAcademischZiekenhuis`
    - `dim_status`: `Code, Omschrijving, Groep, Bekostigd (Boolean)`
    - `fact_deelname`: `_feit_id, levering, _persoon_id, Recordsoort (BRD/HRD), BRIN, Opleidingscode, Bekostigingsjaar (Int64, nooit null als de levering bekend is), Bekostigingsindicatie, CodeBekostigingstatus, Inschrijvingvolgnummer`, plus de overige BRD/HRD-velden behalve persoons- en opleidingsattributen
    - `fact_resultaat`: idem met `Resultaatvolgnummer`, `DatumDiploma`, `JointDegreeFactor` (Recordsoort BRR/HRR)
    - `fact_status`: `_feit_id, levering, Bron ("deelname"/"resultaat"), Code`
    - `fact_loopbaan`: `levering, _persoon_id`, de verbruiks- en aantallenvelden van BLB

- [ ] **Step 1: Schrijf de falende tests `tests/test_stack.py`**

```python
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
```

- [ ] **Step 2: Schrijf de falende tests `tests/test_star.py`**

```python
from datetime import date

import polars as pl
import pytest

from ho_bekostiging_bestanden.pipeline import run_pipeline
from ho_bekostiging_bestanden.stack import stack_prepared
from ho_bekostiging_bestanden.star import FEIT_ID, PERSOON_ID, STAR_TABELLEN, build_star

SLEUTELS = {
    "dim_levering": "levering",
    "dim_persoon": PERSOON_ID,
    "dim_instelling": "BRIN",
    "dim_opleiding": "Opleidingscode",
    "dim_status": "Code",
}
VERWIJZINGEN = [
    ("fact_deelname", "levering", "dim_levering"),
    ("fact_deelname", PERSOON_ID, "dim_persoon"),
    ("fact_deelname", "BRIN", "dim_instelling"),
    ("fact_deelname", "Opleidingscode", "dim_opleiding"),
    ("fact_resultaat", "levering", "dim_levering"),
    ("fact_resultaat", PERSOON_ID, "dim_persoon"),
    ("fact_resultaat", "BRIN", "dim_instelling"),
    ("fact_resultaat", "Opleidingscode", "dim_opleiding"),
    ("fact_status", "Code", "dim_status"),
    ("fact_loopbaan", PERSOON_ID, "dim_persoon"),
]


def _star(tmp_path, *bestanden):
    mappen = []
    for bestand in bestanden:
        doel = tmp_path / "prep" / bestand.stem
        run_pipeline(bestand, doel)
        mappen.append(doel)
    return build_star(stack_prepared(mappen))


@pytest.fixture
def star(tmp_path, vlpbek_bestand, hisbek_bestand):
    return _star(tmp_path, vlpbek_bestand, hisbek_bestand)


def test_alle_tabellen(star):
    assert tuple(star) == STAR_TABELLEN


@pytest.mark.parametrize("tabel,sleutel", SLEUTELS.items())
def test_dimensiesleutels_uniek(star, tabel, sleutel):
    kolom = star[tabel][sleutel]
    assert kolom.null_count() == 0
    assert kolom.n_unique() == star[tabel].height


@pytest.mark.parametrize("feit,sleutel,dim", VERWIJZINGEN)
def test_geen_verweesde_verwijzingen(star, feit, sleutel, dim):
    waarden = set(star[feit][sleutel].drop_nulls())
    assert waarden <= set(star[dim][SLEUTELS[dim]])


def test_brugtabel_verwijst_naar_feiten(star):
    feit_ids = set(star["fact_deelname"][FEIT_ID]) | set(star["fact_resultaat"][FEIT_ID])
    assert set(star["fact_status"][FEIT_ID]) <= feit_ids


def test_fact_deelname_bevat_brd_en_hrd(star):
    feit = star["fact_deelname"]
    assert feit.height == 5
    assert feit["Recordsoort"].value_counts().sort("Recordsoort").rows() == [
        ("BRD", 3), ("HRD", 2)
    ]
    assert feit["Bekostigingsjaar"].null_count() == 0
    assert sorted(feit["Bekostigingsjaar"].unique()) == [2023, 2024, 2025]
    assert "Burgerservicenummer" not in feit.columns
    assert "Opleidingsniveau" not in feit.columns


def test_persoon_zonder_bsn_krijgt_onderwijsnummer(star):
    assert "800010002" in star["dim_persoon"][PERSOON_ID].to_list()


def test_meervoudige_status_wordt_gesplitst(star):
    na_ti = star["fact_deelname"].filter(pl.col("CodeBekostigingstatus") == "na,ti")
    codes = star["fact_status"].filter(pl.col(FEIT_ID) == na_ti[FEIT_ID][0])["Code"]
    assert sorted(codes) == ["na", "ti"]


def test_eigen_instelling(star):
    dim = dict(star["dim_instelling"].select("BRIN", "EigenInstelling").rows())
    assert dim == {"99XX": True, "71AA": False}


def test_graaddatum_in_dim_persoon(star):
    persoon = star["dim_persoon"].filter(pl.col(PERSOON_ID) == "700010001")
    assert persoon["DatumGraadBehaaldBa"][0] == date(2023, 6, 25)


def test_dim_status_compleet(star):
    assert star["dim_status"].height == 34
    assert star["dim_status"].schema["Bekostigd"] == pl.Boolean


def test_alleen_hisbek(tmp_path, hisbek_bestand):
    star = _star(tmp_path, hisbek_bestand)
    assert tuple(star) == STAR_TABELLEN
    assert star["fact_loopbaan"].is_empty()
    assert {"levering", PERSOON_ID} <= set(star["fact_loopbaan"].columns)
    assert star["fact_resultaat"].height == 1


def test_lege_invoer_geeft_lege_tabellen():
    star = build_star({})
    assert tuple(star) == STAR_TABELLEN
    assert all(star[t].is_empty() for t in STAR_TABELLEN if t != "dim_status")
    assert "Bekostigingsjaar" in star["fact_deelname"].columns
```

- [ ] **Step 3: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_stack.py tests/test_star.py -v`
Expected: FAIL met `ModuleNotFoundError` voor `stack` en `star`.

- [ ] **Step 4: Schrijf `src/ho_bekostiging_bestanden/stack.py`**

```python
"""Samenvoegen van prepared leveringen (voorlopig, definitief, historisch)."""

from collections.abc import Sequence
from pathlib import Path

import polars as pl

LABEL_COL = "levering"


def stack_prepared(
    sources: Sequence[Path | str],
    label_col: str = LABEL_COL,
    labels: list[str] | None = None,
) -> dict[str, pl.DataFrame]:
    """Voeg de Parquet-tabellen van meerdere prepared-mappen samen.

    Elke map is één levering. Er komt een leveringskolom (eerste kolom) bij,
    standaard de mapnaam. Tabellen met dezelfde naam worden onder elkaar
    gezet; ontbrekende kolommen worden met ``null`` gevuld.

    Args:
        sources:   Mappen met Parquet-bestanden (één per levering).
        label_col: Naam van de leveringskolom.
        labels:    Labels per map; standaard de mapnamen.

    Returns:
        Dict van tabelnaam naar samengevoegde DataFrame.

    Raises:
        FileNotFoundError: Als een map niet bestaat.
        ValueError:        Als ``labels`` een andere lengte heeft dan ``sources``.
    """
    paths = [Path(s) for s in sources]
    if not paths:
        return {}
    if labels is not None and len(labels) != len(paths):
        raise ValueError(
            f"labels heeft {len(labels)} elementen, sources heeft {len(paths)}"
        )
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"Bronmap niet gevonden: {p}")

    labels = labels or [p.name for p in paths]
    tables: dict[str, list[pl.DataFrame]] = {}
    for path, label in zip(paths, labels, strict=True):
        for parquet in sorted(path.glob("*.parquet")):
            df = pl.read_parquet(parquet).with_columns(pl.lit(label).alias(label_col))
            df = df.select([label_col, *[c for c in df.columns if c != label_col]])
            tables.setdefault(parquet.stem, []).append(df)

    return {
        tabel: pl.concat(frames, how="diagonal_relaxed")
        for tabel, frames in tables.items()
    }
```

- [ ] **Step 5: Schrijf `src/ho_bekostiging_bestanden/star.py`**

```python
"""Dimensionaal model (star schema) uit de gestapelde prepared-tabellen.

Vijf dimensies (levering, persoon, instelling, opleiding, status) en vier
feittabellen (deelname, resultaat, status-brug, loopbaan). Kolommen en typen
worden afgeleid uit de schema-TOML's, zodat ontbrekende leveringen (bijv. geen
HISBEK) lege maar correct gevormde tabellen opleveren.

Publieke API:
    build_star(stacked) -> dict[str, pl.DataFrame]
"""

import polars as pl

from ho_bekostiging_bestanden.decode import STATUS_SCHEIDING, STATUS_VELD
from ho_bekostiging_bestanden.ingest import LEVERING, SCHEMA_PER_LEVERING
from ho_bekostiging_bestanden.metadata import load_codelijst, load_schema
from ho_bekostiging_bestanden.stack import LABEL_COL

PERSOON_ID = "_persoon_id"
FEIT_ID = "_feit_id"
DEELNAME_BRONNEN = ("BRD", "HRD")
RESULTAAT_BRONNEN = ("BRR", "HRR")
LOOPBAAN_BRON = "BLB"
PERSOON_VELDEN = ["Burgerservicenummer", "Onderwijsnummer"]
OPLEIDING_VELDEN = [
    "Opleidingsniveau",
    "OpleidingOnderdeel",
    "IndicatieSectorLG",
    "IndicatieAcademischZiekenhuis",
]
STATUS_CODELIJST = "bekostigingstatus"
BEKOSTIGD_JA = "J"
ONBEKENDE_STATUS = {
    "Omschrijving": "Onbekende code (niet in de PvE)",
    "Groep": "Onbekend",
}

DIM_LEVERING_SCHEMA = {
    LABEL_COL: pl.Utf8,
    "SoortLevering": pl.Utf8,
    "Bekostigingsjaar": pl.Int64,
    "DatumAanmaak": pl.Date,
    "BrinOntvanger": pl.Utf8,
    "Bestandsnaam": pl.Utf8,
}

STAR_TABELLEN = (
    "dim_levering",
    "dim_persoon",
    "dim_instelling",
    "dim_opleiding",
    "dim_status",
    "fact_deelname",
    "fact_resultaat",
    "fact_status",
    "fact_loopbaan",
)

_TYPE_PER_SLEUTEL = {
    "date_fields": pl.Date,
    "bool_fields": pl.Boolean,
    "int_fields": pl.Int64,
    "float_fields": pl.Float64,
}


def _veldtypen(rs: str) -> dict[str, pl.DataType]:
    """Kolomtypen van een recordsoort, afgeleid uit de schema-TOML."""
    for schema_naam in dict.fromkeys(SCHEMA_PER_LEVERING.values()):
        spec = load_schema(schema_naam).get(rs)
        if spec is None:
            continue
        typen: dict[str, pl.DataType] = {veld: pl.Utf8 for veld in spec["fields"]}
        for sleutel, dtype in _TYPE_PER_SLEUTEL.items():
            typen.update({veld: dtype for veld in spec.get(sleutel, [])})
        return typen
    raise KeyError(f"Recordsoort {rs} staat in geen enkel schema")


def _met_template(
    stacked: dict[str, pl.DataFrame], bronnen: tuple[str, ...]
) -> pl.DataFrame:
    """Zet de bronnen onder elkaar, met gegarandeerd alle schemakolommen."""
    template: dict[str, pl.DataType] = {LABEL_COL: pl.Utf8}
    for rs in bronnen:
        template.update(_veldtypen(rs))
    delen = [pl.DataFrame(schema=template)]
    delen += [
        stacked[rs] for rs in bronnen if rs in stacked and not stacked[rs].is_empty()
    ]
    return pl.concat(delen, how="diagonal_relaxed")


def _persoon_id() -> pl.Expr:
    return pl.coalesce(PERSOON_VELDEN).alias(PERSOON_ID)


def _nieuwste_eerst(
    df: pl.DataFrame, dim_levering: pl.DataFrame, sleutel: str, velden: list[str]
) -> pl.DataFrame:
    """Per sleutel de eerste niet-lege waarde per veld, nieuwste levering eerst."""
    aanmaak = dim_levering.select(LABEL_COL, "DatumAanmaak")
    return (
        df.filter(pl.col(sleutel).is_not_null())
        .join(aanmaak, on=LABEL_COL, how="left")
        .sort("DatumAanmaak", descending=True, nulls_last=True)
        .group_by(sleutel, maintain_order=True)
        .agg(pl.col(v).drop_nulls().first() for v in velden)
        .sort(sleutel)
    )


def _dim_levering(stacked: dict[str, pl.DataFrame]) -> pl.DataFrame:
    delen = [pl.DataFrame(schema=DIM_LEVERING_SCHEMA)]
    if LEVERING in stacked:
        delen.append(stacked[LEVERING].select(list(DIM_LEVERING_SCHEMA)))
    return (
        pl.concat(delen, how="vertical_relaxed")
        .unique(LABEL_COL, keep="first", maintain_order=True)
        .sort(LABEL_COL)
    )


def _feiten(
    stacked: dict[str, pl.DataFrame],
    bronnen: tuple[str, ...],
    prefix: str,
    dim_levering: pl.DataFrame,
) -> pl.DataFrame:
    """Feittabel: BRD+HRD of BRR+HRR, met ``_feit_id`` en bekostigingsjaar.

    BRD/BRR hebben geen eigen bekostigingsjaar; dat komt uit de levering.
    Persoons- en opleidingsattributen verhuizen naar de dimensies.
    """
    jaar = dim_levering.select(LABEL_COL, pl.col("Bekostigingsjaar").alias("_jaar"))
    df = (
        _met_template(stacked, bronnen)
        .join(jaar, on=LABEL_COL, how="left")
        .with_columns(
            pl.coalesce("Bekostigingsjaar", "_jaar").alias("Bekostigingsjaar"),
            _persoon_id(),
        )
        .drop("_jaar", *PERSOON_VELDEN, *OPLEIDING_VELDEN)
        .with_row_index("_rij")
        .with_columns(
            pl.concat_str(
                [pl.lit(prefix), pl.col(LABEL_COL), pl.col("_rij").cast(pl.Utf8)],
                separator=":",
            ).alias(FEIT_ID)
        )
        .drop("_rij")
    )
    eerst = [FEIT_ID, LABEL_COL, PERSOON_ID]
    return df.select(eerst + [c for c in df.columns if c not in eerst])


def _graadvelden() -> list[str]:
    return [v for v, t in _veldtypen(LOOPBAAN_BRON).items() if t == pl.Date]


def _fact_loopbaan(stacked: dict[str, pl.DataFrame]) -> pl.DataFrame:
    df = _met_template(stacked, (LOOPBAAN_BRON,)).with_columns(_persoon_id())
    df = df.drop("Recordsoort", *PERSOON_VELDEN, *_graadvelden())
    eerst = [LABEL_COL, PERSOON_ID]
    return df.select(eerst + [c for c in df.columns if c not in eerst])


def _dim_persoon(
    stacked: dict[str, pl.DataFrame], dim_levering: pl.DataFrame
) -> pl.DataFrame:
    graad = _graadvelden()
    kolommen = (LABEL_COL, *PERSOON_VELDEN, *graad)
    delen = []
    for rs in (LOOPBAAN_BRON, *DEELNAME_BRONNEN, *RESULTAAT_BRONNEN):
        df = _met_template(stacked, (rs,))
        delen.append(df.select([c for c in kolommen if c in df.columns]))
    bron = pl.concat(delen, how="diagonal_relaxed").with_columns(_persoon_id())
    return _nieuwste_eerst(bron, dim_levering, PERSOON_ID, [*PERSOON_VELDEN, *graad])


def _dim_opleiding(
    stacked: dict[str, pl.DataFrame], dim_levering: pl.DataFrame
) -> pl.DataFrame:
    velden = [LABEL_COL, "Opleidingscode", *OPLEIDING_VELDEN]
    bron = pl.concat(
        [
            _met_template(stacked, (rs,)).select(velden)
            for rs in (*DEELNAME_BRONNEN, *RESULTAAT_BRONNEN)
        ],
        how="vertical_relaxed",
    )
    return _nieuwste_eerst(bron, dim_levering, "Opleidingscode", OPLEIDING_VELDEN)


def _dim_instelling(
    deelname: pl.DataFrame, resultaat: pl.DataFrame, dim_levering: pl.DataFrame
) -> pl.DataFrame:
    ontvangers = dim_levering["BrinOntvanger"].drop_nulls()
    brins = pl.concat(
        [
            deelname.select("BRIN"),
            resultaat.select("BRIN"),
            dim_levering.select(pl.col("BrinOntvanger").alias("BRIN")),
        ]
    )
    return (
        brins.drop_nulls()
        .unique()
        .sort("BRIN")
        .with_columns(pl.col("BRIN").is_in(ontvangers).alias("EigenInstelling"))
    )


def _fact_status(deelname: pl.DataFrame, resultaat: pl.DataFrame) -> pl.DataFrame:
    delen = [
        feit.select(
            FEIT_ID,
            LABEL_COL,
            pl.lit(bron).alias("Bron"),
            pl.col(STATUS_VELD).str.split(STATUS_SCHEIDING).alias("Code"),
        )
        for feit, bron in ((deelname, "deelname"), (resultaat, "resultaat"))
    ]
    return pl.concat(delen).explode("Code").filter(pl.col("Code").is_not_null())


def _dim_status(fact_status: pl.DataFrame) -> pl.DataFrame:
    """Codelijst plus eventuele codes uit de data die niet in de PvE staan."""
    codelijst = load_codelijst(STATUS_CODELIJST).with_columns(
        (pl.col("Bekostigd") == BEKOSTIGD_JA).alias("Bekostigd")
    )
    onbekend = (
        fact_status.select("Code")
        .unique()
        .filter(~pl.col("Code").is_in(codelijst["Code"]))
        .with_columns(
            *[pl.lit(v).alias(k) for k, v in ONBEKENDE_STATUS.items()],
            pl.lit(False).alias("Bekostigd"),
        )
    )
    return pl.concat([codelijst, onbekend.select(codelijst.columns)]).sort("Code")


def build_star(stacked: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    """Bouw het star schema uit de uitvoer van :func:`stack_prepared`.

    Args:
        stacked: Tabelnaam → gestapelde DataFrame (recordsoorten en ``LEVERING``).

    Returns:
        Dict met de tabellen uit ``STAR_TABELLEN``, in die volgorde. Tabellen
        waarvoor geen bron is, zijn leeg maar hebben hun vaste kolommen.
    """
    dim_levering = _dim_levering(stacked)
    deelname = _feiten(stacked, DEELNAME_BRONNEN, "D", dim_levering)
    resultaat = _feiten(stacked, RESULTAAT_BRONNEN, "R", dim_levering)
    status = _fact_status(deelname, resultaat)
    tabellen = {
        "dim_levering": dim_levering,
        "dim_persoon": _dim_persoon(stacked, dim_levering),
        "dim_instelling": _dim_instelling(deelname, resultaat, dim_levering),
        "dim_opleiding": _dim_opleiding(stacked, dim_levering),
        "dim_status": _dim_status(status),
        "fact_deelname": deelname,
        "fact_resultaat": resultaat,
        "fact_status": status,
        "fact_loopbaan": _fact_loopbaan(stacked),
    }
    return {naam: tabellen[naam] for naam in STAR_TABELLEN}
```

- [ ] **Step 6: Run de tests**

Run: `uv run pytest tests/test_stack.py tests/test_star.py -v`
Expected: alle tests PASS. Faalt `test_geen_verweesde_verwijzingen`, controleer dan eerst of `_persoon_id` in de feiten en in `dim_persoon` op dezelfde manier wordt gemaakt (via `_persoon_id()`).

- [ ] **Step 7: Volledige testsuite, lint en commit**

```bash
uv run pytest && uv run ruff format . && uv run ruff check . && uv run ty check
git add src/ho_bekostiging_bestanden/stack.py src/ho_bekostiging_bestanden/star.py tests/test_stack.py tests/test_star.py
git commit -m "feat(stack,star): leveringen stapelen en star schema (5 dim, 4 fact)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Alles verwerken, `run_star` en CLI `ho star`

**Files:**
- Modify: `src/ho_bekostiging_bestanden/pipeline.py` (toevoegen: `DATAMODEL_MAP`, `run_star`, `Verwerking`, `vind_bestanden`, `verwerk_alles`)
- Modify: `src/ho_bekostiging_bestanden/cli.py` (subcommando `star`)
- Test: `tests/test_scenarios.py`, en een test erbij in `tests/test_cli.py`

**Interfaces:**
- Consumes: `run_pipeline`, `detect_levering` (Task 6); `stack_prepared` (Task 7); `build_star`, `STAR_TABELLEN` (Task 7); `export_frames` (Task 5).
- Produces (in `pipeline.py`):
  - `DATAMODEL_MAP = "datamodel"`
  - `run_star(sources: Sequence[Path | str], target: str | Path) -> dict[str, pl.DataFrame]`: stapelt, bouwt het star schema en schrijft het naar `<target>/datamodel/`.
  - `vind_bestanden(raw: Path) -> list[Path]`: alle herkende bestanden onder `raw` (recursief, gesorteerd).
  - `@dataclass class Verwerking`: `prepared_dirs: list[Path]`, `star: dict[str, pl.DataFrame]`, `validatie: dict[str, pl.DataFrame]` (bestandsnaam → rapport), `fouten: dict[str, str]` (bestandsnaam → foutmelding).
  - `verwerk_alles(raw: Path, prepared: Path, output: Path) -> Verwerking`: verwerkt elk herkend bestand naar `prepared/<bestandsstam>`, vangt een `ValueError` per bestand af (komt in `fouten`, de rest gaat door) en bouwt daarna het star schema in `output`.
- CLI: `ho star <map…> --output <map>`.

- [ ] **Step 1: Schrijf de falende tests `tests/test_scenarios.py`**

```python
"""End-to-end: elke combinatie van leveringen moet een volledig star schema geven."""

import pytest

from ho_bekostiging_bestanden.pipeline import DATAMODEL_MAP, verwerk_alles
from ho_bekostiging_bestanden.star import STAR_TABELLEN

from .conftest import analyse_regels, hisbek_regels, schrijf_bestand

BESTANDEN = {
    "vlpbek": ("VLPBEK_2025_20240115_99XX.csv", lambda: analyse_regels()),
    "defbek": (
        "DEFBEK_2025_20240715_99XX.csv",
        lambda: analyse_regels(statussen=("pi", "mv", "pi")),
    ),
    "hisbek": ("HISBEK_2024_20250301_99XX.csv", hisbek_regels),
}

SCENARIOS = {
    "alle leveringen": ["vlpbek", "defbek", "hisbek"],
    "zonder HISBEK": ["vlpbek", "defbek"],
    "alleen VLPBEK": ["vlpbek"],
    "alleen HISBEK": ["hisbek"],
}


def _raw(tmp_path, soorten):
    raw = tmp_path / "raw"
    raw.mkdir()
    for soort in soorten:
        naam, regels = BESTANDEN[soort]
        schrijf_bestand(raw, naam, regels())
    return raw


@pytest.mark.parametrize("soorten", SCENARIOS.values(), ids=SCENARIOS.keys())
def test_scenario_levert_volledig_star_schema(tmp_path, soorten):
    raw = _raw(tmp_path, soorten)
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.fouten == {}
    assert tuple(resultaat.star) == STAR_TABELLEN
    assert resultaat.star["dim_levering"].height == len(soorten)
    geschreven = {p.stem for p in (tmp_path / "out" / DATAMODEL_MAP).glob("*.parquet")}
    assert geschreven == set(STAR_TABELLEN)
    assert all(rapport.height == 0 for rapport in resultaat.validatie.values())


def test_fout_bestand_stopt_de_rest_niet(tmp_path):
    raw = _raw(tmp_path, ["vlpbek"])
    schrijf_bestand(raw, "DEFBEK_2025_20240715_99XX.csv", analyse_regels()[1:])  # geen VLP
    (raw / "notities.txt").write_text("genegeerd")
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert list(resultaat.fouten) == ["DEFBEK_2025_20240715_99XX.csv"]
    assert "VLP" in resultaat.fouten["DEFBEK_2025_20240715_99XX.csv"]
    assert resultaat.star["dim_levering"].height == 1


def test_lege_map(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    resultaat = verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    assert resultaat.prepared_dirs == []
    assert tuple(resultaat.star) == STAR_TABELLEN
```

- [ ] **Step 2: Voeg de falende CLI-test toe aan `tests/test_cli.py`**

```python
def test_cli_star(tmp_path, vlpbek_bestand, monkeypatch, capsys):
    prep = tmp_path / "prep" / vlpbek_bestand.stem
    monkeypatch.setattr(sys, "argv", ["ho", "verwerk", str(vlpbek_bestand), str(prep)])
    main()
    uit = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["ho", "star", str(prep), "--output", str(uit)])
    main()
    assert "Star schema gebouwd: 9 tabellen" in capsys.readouterr().out
    assert (uit / "datamodel" / "fact_deelname.parquet").exists()
```

- [ ] **Step 3: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_scenarios.py tests/test_cli.py -v`
Expected: FAIL met `ImportError: cannot import name 'DATAMODEL_MAP'` en een argparse-fout voor `star`.

- [ ] **Step 4: Breid `src/ho_bekostiging_bestanden/pipeline.py` uit**

Voeg deze imports toe bovenaan (naast de bestaande):

```python
from collections.abc import Sequence
from dataclasses import dataclass, field

from ho_bekostiging_bestanden.stack import stack_prepared
from ho_bekostiging_bestanden.star import build_star
```

Zet `DATAMODEL_MAP = "datamodel"` onder de imports, voeg `"DATAMODEL_MAP", "Verwerking", "run_star", "verwerk_alles", "vind_bestanden"` toe aan `__all__`, en voeg onderaan toe:

```python
def run_star(
    sources: Sequence[Path | str],
    target: str | Path,
) -> dict[str, pl.DataFrame]:
    """Stapel prepared-mappen, bouw het star schema en schrijf het weg.

    Args:
        sources: Mappen met prepared Parquet-bestanden (één per levering).
        target:  Doelmap; het star schema komt in ``<target>/datamodel/``.

    Returns:
        Dict met de star-schema-tabellen.
    """
    star = build_star(stack_prepared(sources))
    export_frames(star, Path(target) / DATAMODEL_MAP)
    return star


@dataclass
class Verwerking:
    """Uitkomst van :func:`verwerk_alles`."""

    prepared_dirs: list[Path] = field(default_factory=list)
    star: dict[str, pl.DataFrame] = field(default_factory=dict)
    validatie: dict[str, pl.DataFrame] = field(default_factory=dict)
    fouten: dict[str, str] = field(default_factory=dict)


def vind_bestanden(raw: Path) -> list[Path]:
    """Alle herkende leveringen onder ``raw`` (recursief, gesorteerd)."""
    return [
        p for p in sorted(Path(raw).rglob("*"))
        if p.is_file() and detect_levering(p) is not None
    ]


def verwerk_alles(raw: Path, prepared: Path, output: Path) -> Verwerking:
    """Verwerk alle herkende bestanden in ``raw`` en bouw het star schema.

    Een bestand dat niet verwerkt kan worden (bijv. zonder VLP) komt in
    ``fouten``; de overige bestanden gaan gewoon door.

    Args:
        raw:      Map met ruwe bestanden.
        prepared: Map voor de prepared-tabellen (één submap per bestand).
        output:   Map voor het star schema.

    Returns:
        :class:`Verwerking` met prepared-mappen, star schema, validatie en fouten.
    """
    resultaat = Verwerking()
    for bestand in vind_bestanden(raw):
        doel = Path(prepared) / bestand.stem
        try:
            frames = run_pipeline(bestand, doel)
        except ValueError as fout:
            resultaat.fouten[bestand.name] = str(fout)
            continue
        resultaat.prepared_dirs.append(doel)
        resultaat.validatie[bestand.name] = frames[VALIDATIE]
    resultaat.star = run_star(resultaat.prepared_dirs, output)
    return resultaat
```

- [ ] **Step 5: Breid `src/ho_bekostiging_bestanden/cli.py` uit**

Werk de module-docstring bij (`ho star <map…> --output <map>` toevoegen), wijzig de import naar `from ho_bekostiging_bestanden.pipeline import run_pipeline, run_star`, voeg de handler toe:

```python
def _star(args: argparse.Namespace) -> None:
    star = run_star(args.sources, args.output)
    total = sum(df.height for df in star.values())
    print(f"Star schema gebouwd: {len(star)} tabellen, {total} rijen → {args.output}")
```

en voeg in `build_parser()` vóór `return parser` toe:

```python
    p_star = sub.add_parser("star", help="Bouw star schema vanuit prepared-mappen")
    p_star.add_argument(
        "sources",
        nargs="+",
        type=Path,
        help="Mappen met Parquet-bestanden (één per levering)",
    )
    p_star.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Doelmap; het star schema komt in <output>/datamodel/",
    )
    p_star.set_defaults(func=_star)
```

- [ ] **Step 6: Run de tests**

Run: `uv run pytest -v`
Expected: alle tests PASS, ook de vier scenario's.

- [ ] **Step 7: Lint en commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add src/ho_bekostiging_bestanden/pipeline.py src/ho_bekostiging_bestanden/cli.py tests/test_scenarios.py tests/test_cli.py
git commit -m "feat(pipeline): verwerk_alles, run_star en ho star; werkt ook zonder HISBEK

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Synthetische demo-data

**Files:**
- Create: `src/ho_bekostiging_bestanden/demo.py` (generator + regelbouwer)
- Create: `scripts/genereer_demo.py` (dunne wrapper)
- Create: `data/01-raw/demo/*.csv` (gegenereerd, in git)
- Modify: `tests/conftest.py` (regelbouwer uit `demo.py` gebruiken; `demo_star`-fixture)
- Test: `tests/test_demo.py`

**Interfaces:**
- Consumes: `load_schema` (Task 2); `verwerk_alles` (Task 8).
- Produces (in `demo.py`):
  - `PAD_TOT = 25`
  - `maak_regel(schema_naam: str, rs: str, **waarden: str) -> str`
  - `schrijf_bestand(map_: Path, naam: str, regels: list[str]) -> Path` (CRLF, opgevuld tot `PAD_TOT` velden)
  - `genereer_demo(doel: Path = DOEL) -> list[Path]`: schrijft `VLPBEK_2025_20240115_99XX.csv`, `VLPBEK_2026_20250115_99XX.csv`, `DEFBEK_2025_20240715_99XX.csv` en `HISBEK_2024_20250301_99XX.csv`. Het resultaat is deterministisch (vaste seed).
- Produces (in `tests/conftest.py`): session-fixture `demo_star -> dict[str, pl.DataFrame]` (star schema van de demo-data) en `DEMO_RAW: Path`.

- [ ] **Step 1: Schrijf de falende tests `tests/test_demo.py`**

```python
import polars as pl

from ho_bekostiging_bestanden.demo import genereer_demo
from ho_bekostiging_bestanden.pipeline import verwerk_alles

from .conftest import DEMO_RAW

VERWACHT = {
    "VLPBEK_2025_20240115_99XX.csv",
    "VLPBEK_2026_20250115_99XX.csv",
    "DEFBEK_2025_20240715_99XX.csv",
    "HISBEK_2024_20250301_99XX.csv",
}


def test_generator_is_deterministisch(tmp_path):
    a = genereer_demo(tmp_path / "a")
    b = genereer_demo(tmp_path / "b")
    assert {p.name for p in a} == VERWACHT
    for pa, pb in zip(sorted(a), sorted(b), strict=True):
        assert pa.read_bytes() == pb.read_bytes()


def test_demo_in_git_is_actueel(tmp_path):
    for pad in genereer_demo(tmp_path):
        assert (DEMO_RAW / pad.name).read_bytes() == pad.read_bytes(), pad.name


def test_demo_verwerkt_zonder_fouten_of_meldingen(tmp_path):
    resultaat = verwerk_alles(DEMO_RAW, tmp_path / "prep", tmp_path / "out")
    assert resultaat.fouten == {}
    for naam, rapport in resultaat.validatie.items():
        assert rapport.height == 0, (naam, rapport.to_dicts())


def test_demo_is_gevarieerd(demo_star):
    assert demo_star["dim_levering"].height == 4
    assert demo_star["fact_status"]["Code"].n_unique() >= 10
    assert "71AA" in demo_star["dim_instelling"]["BRIN"].to_list()
    assert demo_star["dim_persoon"]["Burgerservicenummer"].null_count() > 0
    assert demo_star["fact_loopbaan"]["AantalBekostigdeInschrijvingenMa_NVT"].any()


def test_definitief_herstelt_te_laat_aangeleverd(demo_star):
    feit = demo_star["fact_deelname"].join(
        demo_star["dim_levering"], on="levering"
    ).filter(pl.col("Bekostigingsjaar") == 2025)
    ti = feit.filter(pl.col("CodeBekostigingstatus").str.contains("ti"))
    per_soort = dict(ti.group_by("SoortLevering").len().rows())
    assert per_soort["DEFBEK"] < per_soort["VLPBEK"]
```

- [ ] **Step 2: Werk `tests/conftest.py` bij**

Verwijder de eigen `PAD_TOT`, `maak_regel` en `schrijf_bestand` uit `conftest.py` en importeer ze uit het package (één implementatie, Boy Scout). Voeg de demo-fixture toe:

```python
from ho_bekostiging_bestanden.demo import maak_regel, schrijf_bestand
from ho_bekostiging_bestanden.pipeline import verwerk_alles

DEMO_RAW = Path(__file__).parents[1] / "data" / "01-raw" / "demo"

__all__ = ["DEMO_RAW", "analyse_regels", "hisbek_regels", "maak_regel", "schrijf_bestand"]


@pytest.fixture(scope="session")
def demo_star(tmp_path_factory) -> dict:
    """Star schema van de demo-data (één keer per testsessie gebouwd)."""
    basis = tmp_path_factory.mktemp("demo")
    return verwerk_alles(DEMO_RAW, basis / "prep", basis / "out").star
```

De imports `from .conftest import maak_regel, schrijf_bestand` in eerdere testbestanden blijven werken, omdat `conftest` ze opnieuw exporteert.

- [ ] **Step 3: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_demo.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named 'ho_bekostiging_bestanden.demo'`

- [ ] **Step 4: Schrijf `src/ho_bekostiging_bestanden/demo.py`**

```python
"""Synthetische demo-bestanden (VLPBEK/DEFBEK/HISBEK) volgens de PvE-veldindeling.

Alle personen, nummers en opleidingscodes zijn fictief. Regels worden
opgebouwd vanuit de schema-TOML's en, net als echte DUO-bestanden, opgevuld
tot 25 velden met CRLF-regeleinden. De uitkomst is deterministisch.
"""

import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ho_bekostiging_bestanden.metadata import load_schema

SEED = 42
DOEL = Path("data/01-raw/demo")
PAD_TOT = 25  # aantal velden waarop DUO elke regel opvult
BRIN_EIGEN = "99XX"
BRIN_ANDER = "71AA"
AANTAL_PERSONEN = 150
ELKE_ZONDER_BSN = 12  # elke 12e persoon heeft alleen een onderwijsnummer
KANS_ANDERE_INSTELLING = 0.1
KANS_RESULTAAT = 0.3
KANS_NVT = 0.05
HISBEK_OVERSLAAN = 3  # persoon mist een HISBEK-jaar als (nr + jaar) % 3 == 0
HISBEK_GRAAD_ELKE = 5  # elke 5e persoon heeft een historische graad

VOORLOPIG = [(2025, date(2024, 1, 15)), (2026, date(2025, 1, 15))]
DEFINITIEF = [(2025, date(2024, 7, 15))]
HISBEK = (2024, date(2025, 3, 1))
HISBEK_JAREN = (2021, 2022, 2023, 2024)

# Fictieve opleidingen: (code, niveau, fase, onderdeel, bekostigingsniveau, BaMa)
OPLEIDINGEN = [
    ("34001", "HBO-BA", "B", "TECHNIEK", "HOOG", "B"),
    ("34002", "HBO-BA", "B", "ECONOMIE", "LAAG", "B"),
    ("34003", "HBO-AD", "A", "ECONOMIE", "LAAG", "D"),
    ("34004", "HBO-MA", "M", "GEZONDHEIDSZORG", "HOOG", "M"),
    ("34005", "HBO-BA", "B", "ONDERWIJS", "LAAG", "B"),
    ("34006", "HBO-BA", "B", "TAAL_EN_CULTUUR", "LAAG", "B"),
    ("56001", "WO-BA", "B", "RECHT", "LAAG", "B"),
    ("56002", "WO-MA", "M", "GEDRAG_EN_MAATSCHAPPIJ", "LAAG", "M"),
]
DEELNAME_STATUS = {
    "pi": 70, "mv": 8, "jl": 5, "ti": 4, "ng": 3, "nf": 2,
    "na": 2, "nr": 2, "pd": 2, "ex": 1, "na,ti": 1,
}
RESULTAAT_STATUS = {"pg": 60, "np": 15, "mu": 8, "mt": 7, "tg": 5, "nb": 5}
BEKOSTIGD = {"pi", "pd", "pg"}
# Kans dat een voorlopige status in de definitieve levering "pi" wordt.
DEF_HERSTEL = {"ti": 0.6, "nr": 0.5, "na,ti": 0.5}
ONDERWIJSVORM = {"VT": 75, "DT": 15, "DU": 10}
PROPEDEUSE_FASE = "D"


@dataclass(frozen=True)
class _Persoon:
    nr: int
    bsn: str
    onr: str
    opleiding: tuple[str, str, str, str, str, str]
    brins: tuple[str, ...]
    onderwijsvorm: str


def maak_regel(schema_naam: str, rs: str, **waarden: str) -> str:
    """Bouw één ``|``-regel volgens het schema; niet opgegeven velden blijven leeg.

    Raises:
        KeyError: Als een veld niet in het schema van ``rs`` staat.
    """
    velden = load_schema(schema_naam)[rs]["fields"]
    onbekend = set(waarden) - set(velden)
    if onbekend:
        raise KeyError(f"Onbekende velden voor {rs}: {sorted(onbekend)}")
    return "|".join(
        rs if veld == "Recordsoort" else waarden.get(veld, "") for veld in velden
    )


def schrijf_bestand(map_: Path, naam: str, regels: list[str]) -> Path:
    """Schrijf regels met CRLF, opgevuld tot minstens ``PAD_TOT`` velden."""
    map_.mkdir(parents=True, exist_ok=True)
    opgevuld = [r + "|" * max(PAD_TOT - 1 - r.count("|"), 0) for r in regels]
    pad = map_ / naam
    pad.write_bytes(("\r\n".join(opgevuld) + "\r\n").encode("utf-8"))
    return pad


def _kies(rng: random.Random, gewichten: dict[str, int]) -> str:
    return rng.choices(list(gewichten), weights=list(gewichten.values()))[0]


def _jn(waar: bool) -> str:
    return "J" if waar else "N"


def _d(dag: date) -> str:
    return dag.strftime("%Y%m%d")


def _personen(rng: random.Random) -> list[_Persoon]:
    personen = []
    for nr in range(1, AANTAL_PERSONEN + 1):
        extra = rng.random() < KANS_ANDERE_INSTELLING
        personen.append(
            _Persoon(
                nr=nr,
                bsn="" if nr % ELKE_ZONDER_BSN == 0 else f"7000{nr:05d}",
                onr=f"8000{nr:05d}",
                opleiding=rng.choice(OPLEIDINGEN),
                brins=(BRIN_EIGEN, BRIN_ANDER) if extra else (BRIN_EIGEN,),
                onderwijsvorm=_kies(rng, ONDERWIJSVORM),
            )
        )
    # Zoals DUO: oplopend op BSN, personen met alleen een onderwijsnummer achteraan.
    return sorted(personen, key=lambda p: (p.bsn == "", p.bsn, p.onr))


def _deelname(p: _Persoon, brin: str, jaar: int, status: str) -> dict[str, str]:
    code, niveau, fase, onderdeel, bniveau, bama = p.opleiding
    codes = set(status.split(","))
    start = date(jaar - 3, 9, 1) if "mv" in codes else date(jaar - 2, 9, 1)
    aanlevering = date(jaar - 1, 3, 1) if "ti" in codes else date(start.year, 9, 15)
    return {
        "Burgerservicenummer": p.bsn,
        "Onderwijsnummer": p.onr,
        "BRIN": brin,
        "Inschrijvingvolgnummer": f"{brin}{p.nr:05d}{start.year}",
        "Bekostigingsindicatie": _jn(status in BEKOSTIGD),
        "CodeBekostigingstatus": status,
        "Bekostigingsniveau": bniveau,
        "Opleidingscode": code,
        "Opleidingsniveau": niveau,
        "Opleidingsfase": fase,
        "DatumInschrijving": _d(start),
        "DatumUitschrijving": _d(date(start.year + 1, 8, 31)),
        "EersteInschrijving": _jn("jl" not in codes),
        "Inschrijvingsvorm": "E" if "ex" in codes else "S",
        "Onderwijsvorm": p.onderwijsvorm,
        "DatumEersteAanlevering": _d(aanlevering),
        "Bekostigingsduur": "12",
        "OpleidingOnderdeel": onderdeel,
        "Bekostigingscode": "BEKOSTIGD",
        "IndicatieSectorLG": "N",
        "IndicatieBaMa": bama,
        "IndicatieAcademischZiekenhuis": "N",
        "IndicatieNationaliteitsvoorwaardeSF": _jn("nr" not in codes),
        "IndicatieGBARelatie": _jn("na" not in codes),
    }


def _resultaat(p: _Persoon, jaar: int, status: str) -> dict[str, str]:
    code, niveau, fase, onderdeel, bniveau, bama = p.opleiding
    diploma = {"mt": date(jaar - 2, 11, 1), "mu": date(jaar - 3, 6, 25)}.get(
        status, date(jaar - 2, 6, 25)
    )
    aanlevering = date(diploma.year, 12, 1) if status == "tg" else date(diploma.year, 7, 15)
    return {
        "Burgerservicenummer": p.bsn,
        "Onderwijsnummer": p.onr,
        "BRIN": BRIN_EIGEN,
        "Resultaatvolgnummer": f"R{p.nr:05d}{diploma.year}",
        "Bekostigingsindicatie": _jn(status in BEKOSTIGD),
        "CodeBekostigingstatus": status,
        "Bekostigingsniveau": bniveau,
        "JointDegreeFactor": "1",
        "Opleidingscode": code,
        "Opleidingsniveau": niveau,
        "Opleidingsfase": PROPEDEUSE_FASE if status == "np" else fase,
        "EersteGraad": _jn(status != "np"),
        "DatumDiploma": _d(diploma),
        "Onderwijsvorm": p.onderwijsvorm,
        "DatumEersteAanlevering": _d(aanlevering),
        "OpleidingOnderdeel": onderdeel,
        "Bekostigingscode": "BEKOSTIGD",
        "IndicatieSectorLG": "N",
        "IndicatieBaMa": bama,
        "IndicatieAcademischZiekenhuis": "N",
        "IndicatieGraadTeltVoorBekostigingsloopbaan": _jn(status != "np"),
        "IndicatieNationaliteitsvoorwaardeSF": "J",
        "IndicatieGBARelatie": "J",
    }


def _loopbaan(p: _Persoon, jaar: int, graad: date | None) -> dict[str, str]:
    rng = random.Random(f"{SEED}-{p.nr}-{jaar}")
    waarden = {"Burgerservicenummer": p.bsn, "Onderwijsnummer": p.onr}
    if graad is not None:
        waarden["DatumGraadBehaaldBa"] = _d(graad)
    for veld in load_schema("analyse")["BLB"]["int_fields"]:
        waarden[veld] = "-1" if rng.random() < KANS_NVT else str(rng.randint(0, 3))
    return waarden


def _trek_statussen(
    rng: random.Random, personen: list[_Persoon]
) -> tuple[dict[tuple[int, str], str], dict[int, str]]:
    deelnames = {
        (p.nr, brin): _kies(rng, DEELNAME_STATUS) for p in personen for brin in p.brins
    }
    resultaten = {
        p.nr: _kies(rng, RESULTAAT_STATUS)
        for p in personen
        if rng.random() < KANS_RESULTAAT
    }
    return deelnames, resultaten


def _herstel(
    rng: random.Random, deelnames: dict[tuple[int, str], str]
) -> dict[tuple[int, str], str]:
    return {
        sleutel: "pi" if rng.random() < DEF_HERSTEL.get(status, 0) else status
        for sleutel, status in deelnames.items()
    }


def _analysebestand(
    personen: list[_Persoon],
    jaar: int,
    aanmaak: date,
    deelnames: dict[tuple[int, str], str],
    resultaten: dict[int, str],
) -> list[str]:
    regels = [
        maak_regel("analyse", "VLP", BRIN=BRIN_EIGEN, Bekostigingsjaar=str(jaar),
                   DatumAanmaak=_d(aanmaak))
    ]
    tel = {"BLB": 0, "BRD": 0, "BRR": 0}
    for p in personen:
        status_r = resultaten.get(p.nr)
        graad = date(jaar - 2, 6, 25) if status_r == "pg" else None
        regels.append(maak_regel("analyse", "BLB", **_loopbaan(p, jaar, graad)))
        tel["BLB"] += 1
        for brin in p.brins:
            regels.append(
                maak_regel("analyse", "BRD", **_deelname(p, brin, jaar, deelnames[(p.nr, brin)]))
            )
            tel["BRD"] += 1
        if status_r is not None:
            regels.append(maak_regel("analyse", "BRR", **_resultaat(p, jaar, status_r)))
            tel["BRR"] += 1
    regels.append(
        maak_regel("analyse", "SLR", **{f"Aantal{rs}records": str(n) for rs, n in tel.items()})
    )
    return regels


def _hisbek(rng: random.Random, personen: list[_Persoon], aanmaak: date) -> list[str]:
    regels = [maak_regel("hisbek", "VLP", BRIN=BRIN_EIGEN, DatumAanmaak=_d(aanmaak))]
    tel = {"HRD": 0, "HRR": 0}
    for p in personen:
        for jaar in HISBEK_JAREN:
            if (p.nr + jaar) % HISBEK_OVERSLAAN == 0:
                continue
            status = _kies(rng, DEELNAME_STATUS)
            codes = set(status.split(","))
            ects = "60.0" if status in BEKOSTIGD else ""
            waarden = _deelname(p, BRIN_EIGEN, jaar, status) | {
                "Bekostigingsjaar": str(jaar),
                "ECTS": ects,
                "ECTSBekostigd": ects,
                "IndicatieWoonplaatsVereiste": _jn("na" not in codes),
            }
            regels.append(maak_regel("hisbek", "HRD", **waarden))
            tel["HRD"] += 1
        if p.nr % HISBEK_GRAAD_ELKE == 0:
            jaar = HISBEK_JAREN[-1]
            waarden = _resultaat(p, jaar, "pg") | {
                "Bekostigingsjaar": str(jaar),
                "IndicatieWoonplaatsVereiste": "J",
            }
            regels.append(maak_regel("hisbek", "HRR", **waarden))
            tel["HRR"] += 1
    regels.append(
        maak_regel("hisbek", "SLR", **{f"Aantal{rs}records": str(n) for rs, n in tel.items()})
    )
    return regels


def _naam(soort: str, jaar: int, aanmaak: date) -> str:
    return f"{soort}_{jaar}_{_d(aanmaak)}_{BRIN_EIGEN}.csv"


def genereer_demo(doel: Path = DOEL) -> list[Path]:
    """Schrijf de vier demo-bestanden naar ``doel`` en geef de paden terug."""
    personen = _personen(random.Random(SEED))
    trekkingen = {
        jaar: _trek_statussen(random.Random(f"{SEED}-{jaar}"), personen)
        for jaar, _ in VOORLOPIG
    }
    paden = []
    for jaar, aanmaak in VOORLOPIG:
        deelnames, resultaten = trekkingen[jaar]
        regels = _analysebestand(personen, jaar, aanmaak, deelnames, resultaten)
        paden.append(schrijf_bestand(doel, _naam("VLPBEK", jaar, aanmaak), regels))
    for jaar, aanmaak in DEFINITIEF:
        deelnames, resultaten = trekkingen[jaar]
        hersteld = _herstel(random.Random(f"{SEED}-def-{jaar}"), deelnames)
        regels = _analysebestand(personen, jaar, aanmaak, hersteld, resultaten)
        paden.append(schrijf_bestand(doel, _naam("DEFBEK", jaar, aanmaak), regels))
    jaar, aanmaak = HISBEK
    regels = _hisbek(random.Random(f"{SEED}-his"), personen, aanmaak)
    paden.append(schrijf_bestand(doel, _naam("HISBEK", jaar, aanmaak), regels))
    return paden
```

- [ ] **Step 5: Schrijf `scripts/genereer_demo.py`**

```python
"""Genereer de synthetische demo-bestanden in data/01-raw/demo/.

Gebruik:
    uv run python scripts/genereer_demo.py [doelmap]
"""

import sys
from pathlib import Path

from ho_bekostiging_bestanden.demo import DOEL, genereer_demo

if __name__ == "__main__":
    doel = Path(sys.argv[1]) if len(sys.argv) > 1 else DOEL
    for pad in genereer_demo(doel):
        print(f"Geschreven: {pad}")
```

- [ ] **Step 5b: Schrijf `.gitattributes`** zodat git de CRLF-regeleinden van de demo-bestanden niet omzet (anders faalt `test_demo_in_git_is_actueel` in CI op Linux):

```gitattributes
# DUO-bestanden hebben CRLF-regeleinden; git mag ze niet omzetten.
data/01-raw/demo/*.csv -text
```

- [ ] **Step 6: Genereer de demo-bestanden**

Run: `uv run python scripts/genereer_demo.py`
Expected: vier regels `Geschreven: data/01-raw/demo/…csv`.

- [ ] **Step 7: Run de tests**

Run: `uv run pytest -v`
Expected: alle tests PASS. Faalt `test_demo_verwerkt_zonder_fouten_of_meldingen`, pas dan de **generator** aan (niet de validatie): de melding zegt welk veld of welke code niet klopt.

- [ ] **Step 8: Lint en commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add .gitattributes src/ho_bekostiging_bestanden/demo.py scripts/genereer_demo.py data/01-raw/demo tests/
git commit -m "feat(demo): synthetische VLPBEK/DEFBEK/HISBEK-bestanden met vaste seed

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Indicatoren voor het dashboard

**Files:**
- Create: `src/ho_bekostiging_bestanden/indicatoren.py`
- Test: `tests/test_indicatoren.py`

**Interfaces:**
- Consumes: `build_star` en de kolommen uit Task 7; `verwerk_alles` (Task 8); de testhelpers (Task 3/9).
- Produces (pure functies, geen Streamlit):
  - Constanten `VOORLOPIG = "VLPBEK"`, `DEFINITIEF = "DEFBEK"`, `HISTORISCH = "HISBEK"`, `BUITEN_BEOORDELING = "mv"`.
  - `heeft_soort(star, soort: str) -> bool`
  - `actuele_leveringen(star, soort: str) -> list[str]`: per bekostigingsjaar het label (`levering`) van de nieuwste levering van die soort.
  - `feiten(star, feit: str, leveringen: list[str], niveaus: list[str] | None = None) -> pl.DataFrame`: `feit` is `"fact_deelname"` of `"fact_resultaat"`. Alleen de eigen instelling, met extra kolommen `SoortLevering`, `Opleidingsniveau` en `Beoordeeld` (Boolean: status bevat geen `mv`).
  - `trechter(df) -> pl.DataFrame[Stap, Aantal]` met de stappen `"In bestand"`, `"Beoordeeld"`, `"Bekostigd"`.
  - `redenen_niet_bekostigd(df, star) -> pl.DataFrame[Groep, Code, Omschrijving, Aantal]`, gesorteerd op aflopend `Aantal`.
  - `per_opleiding(df) -> pl.DataFrame[Opleidingscode, Opleidingsniveau, Totaal, Bekostigd, AandeelBekostigd]`, alleen beoordeelde rijen.
  - `voorlopig_vs_definitief(star) -> pl.DataFrame[Bekostigingsjaar, Voorlopig, Definitief, Aantal]`: alleen deelnames waarvan de status veranderde.
  - `historie(star) -> pl.DataFrame[Bekostigingsjaar, Bron, Totaal, Bekostigd]`
  - Alle functies geven een leeg, correct gevormd frame als de benodigde levering ontbreekt.

- [ ] **Step 1: Schrijf de falende tests `tests/test_indicatoren.py`**

```python
import polars as pl
import pytest

from ho_bekostiging_bestanden import indicatoren as ind
from ho_bekostiging_bestanden.pipeline import verwerk_alles

from .conftest import analyse_regels, hisbek_regels, maak_regel, schrijf_bestand


def _star(tmp_path, bestanden):
    raw = tmp_path / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for naam, regels in bestanden.items():
        schrijf_bestand(raw, naam, regels)
    return verwerk_alles(raw, tmp_path / "prep", tmp_path / "out").star


@pytest.fixture
def star(tmp_path):
    return _star(tmp_path, {
        "VLPBEK_2025_20240115_99XX.csv": analyse_regels(),
        "DEFBEK_2025_20240715_99XX.csv": analyse_regels(statussen=("pi", "mv", "pi")),
        "HISBEK_2024_20250301_99XX.csv": hisbek_regels(),
    })


def _deelnames(star, soort):
    return ind.feiten(star, "fact_deelname", ind.actuele_leveringen(star, soort))


def test_feiten_alleen_eigen_instelling(star):
    df = _deelnames(star, ind.VOORLOPIG)
    assert df.height == 2
    assert set(df["BRIN"]) == {"99XX"}
    assert {"SoortLevering", "Opleidingsniveau", "Beoordeeld"} <= set(df.columns)


def test_trechter(star):
    assert ind.trechter(_deelnames(star, ind.VOORLOPIG)).rows() == [
        ("In bestand", 2), ("Beoordeeld", 2), ("Bekostigd", 1)
    ]


def test_trechter_telt_mv_niet_als_beoordeeld(tmp_path):
    regels = analyse_regels(statussen=("mv", "pi", "pi"))
    star = _star(tmp_path, {"VLPBEK_2025_20240115_99XX.csv": regels})
    df = ind.feiten(star, "fact_deelname", ind.actuele_leveringen(star, ind.VOORLOPIG))
    assert ind.trechter(df)["Aantal"].to_list() == [2, 1, 1]


def test_redenen_niet_bekostigd(star):
    redenen = ind.redenen_niet_bekostigd(_deelnames(star, ind.VOORLOPIG), star)
    assert sorted(redenen.select("Code", "Aantal").rows()) == [("na", 1), ("ti", 1)]
    assert set(redenen["Groep"]) == {"Status van de student", "Aanlevering"}


def test_per_opleiding(star):
    rij = ind.per_opleiding(_deelnames(star, ind.VOORLOPIG)).row(0, named=True)
    assert rij == {
        "Opleidingscode": "34001",
        "Opleidingsniveau": "HBO-BA",
        "Totaal": 2,
        "Bekostigd": 1,
        "AandeelBekostigd": 0.5,
    }


def test_voorlopig_vs_definitief(star):
    assert ind.voorlopig_vs_definitief(star).rows() == [(2025, "na,ti", "pi", 1)]


def test_historie(star):
    assert ind.historie(star).rows() == [
        (2023, "deelname", 1, 1),
        (2024, "deelname", 1, 0),
        (2024, "resultaat", 1, 1),
    ]


def test_zonder_defbek_en_hisbek(tmp_path):
    star = _star(tmp_path, {"VLPBEK_2025_20240115_99XX.csv": analyse_regels()})
    assert not ind.heeft_soort(star, ind.DEFINITIEF)
    assert ind.voorlopig_vs_definitief(star).is_empty()
    assert ind.historie(star).columns == ["Bekostigingsjaar", "Bron", "Totaal", "Bekostigd"]
    assert ind.historie(star).is_empty()


def test_actuele_levering_is_nieuwste(tmp_path):
    oud = analyse_regels()
    nieuw = analyse_regels()
    nieuw[0] = maak_regel("analyse", "VLP", BRIN="99XX", Bekostigingsjaar="2025",
                          DatumAanmaak="20240315")
    star = _star(tmp_path, {
        "VLPBEK_2025_20240115_99XX.csv": oud,
        "VLPBEK_2025_20240315_99XX.csv": nieuw,
    })
    assert ind.actuele_leveringen(star, ind.VOORLOPIG) == ["VLPBEK_2025_20240315_99XX"]


def test_lege_invoer_geeft_lege_frames(tmp_path):
    star = _star(tmp_path, {})
    df = ind.feiten(star, "fact_deelname", [])
    assert df.is_empty()
    assert ind.trechter(df)["Aantal"].to_list() == [0, 0, 0]
    assert ind.redenen_niet_bekostigd(df, star).is_empty()
    assert ind.per_opleiding(df).is_empty()


def test_demo_heeft_alle_grafieken(demo_star):
    deelnames = ind.feiten(
        demo_star, "fact_deelname", ind.actuele_leveringen(demo_star, ind.DEFINITIEF)
    )
    assert ind.trechter(deelnames)["Aantal"][0] > 0
    assert not ind.redenen_niet_bekostigd(deelnames, demo_star).is_empty()
    assert not ind.voorlopig_vs_definitief(demo_star).is_empty()
    assert ind.historie(demo_star)["Bekostigingsjaar"].n_unique() == 4
    assert isinstance(ind.per_opleiding(deelnames), pl.DataFrame)
```

- [ ] **Step 2: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_indicatoren.py -v`
Expected: FAIL met `ImportError: cannot import name 'indicatoren'`

- [ ] **Step 3: Schrijf `src/ho_bekostiging_bestanden/indicatoren.py`**

```python
"""Indicatoren voor het dashboard, berekend op het star schema.

Pure functies zonder Streamlit, zodat ze testbaar zijn en de app alleen hoeft
te tonen. Alle functies werken alleen met de eigen instelling (``EigenInstelling``)
en geven een leeg, correct gevormd frame als de benodigde levering ontbreekt.
"""

import polars as pl

from ho_bekostiging_bestanden.decode import STATUS_SCHEIDING, STATUS_VELD
from ho_bekostiging_bestanden.star import FEIT_ID, PERSOON_ID
from ho_bekostiging_bestanden.stack import LABEL_COL

VOORLOPIG = "VLPBEK"
DEFINITIEF = "DEFBEK"
HISTORISCH = "HISBEK"
# Deelnames met status mv vallen buiten de beoordeling (PvE §17.5). [Te checken]
BUITEN_BEOORDELING = "mv"
TRECHTER_STAPPEN = ("In bestand", "Beoordeeld", "Bekostigd")
FEIT_BRON = {"fact_deelname": "deelname", "fact_resultaat": "resultaat"}
DEELNAME_SLEUTEL = ["Bekostigingsjaar", "BRIN", "Inschrijvingvolgnummer", PERSOON_ID]

_REDENEN_SCHEMA = {"Groep": pl.Utf8, "Code": pl.Utf8, "Omschrijving": pl.Utf8, "Aantal": pl.UInt32}
_VERSCHIL_SCHEMA = {
    "Bekostigingsjaar": pl.Int64,
    "Voorlopig": pl.Utf8,
    "Definitief": pl.Utf8,
    "Aantal": pl.UInt32,
}


def heeft_soort(star: dict[str, pl.DataFrame], soort: str) -> bool:
    """Is er minstens één levering van deze soort (VLPBEK/DEFBEK/HISBEK)?"""
    return soort in star["dim_levering"]["SoortLevering"].to_list()


def actuele_leveringen(star: dict[str, pl.DataFrame], soort: str) -> list[str]:
    """Per bekostigingsjaar het label van de nieuwste levering van ``soort``."""
    return (
        star["dim_levering"]
        .filter(pl.col("SoortLevering") == soort)
        .sort("DatumAanmaak", descending=True)
        .unique("Bekostigingsjaar", keep="first")
        .sort("Bekostigingsjaar")[LABEL_COL]
        .to_list()
    )


def feiten(
    star: dict[str, pl.DataFrame],
    feit: str,
    leveringen: list[str],
    niveaus: list[str] | None = None,
) -> pl.DataFrame:
    """Feitrijen van de eigen instelling voor de gekozen leveringen.

    Args:
        star:       Uitvoer van :func:`build_star`.
        feit:       ``"fact_deelname"`` of ``"fact_resultaat"``.
        leveringen: Labels uit ``dim_levering.levering``.
        niveaus:    Optioneel filter op ``Opleidingsniveau``.

    Returns:
        Feitrijen met extra kolommen ``SoortLevering``, ``Opleidingsniveau``
        en ``Beoordeeld``.
    """
    eigen = star["dim_instelling"].filter(pl.col("EigenInstelling")).select("BRIN")
    df = (
        star[feit]
        .filter(pl.col(LABEL_COL).is_in(leveringen))
        .join(eigen, on="BRIN", how="semi")
        .join(star["dim_levering"].select(LABEL_COL, "SoortLevering"), on=LABEL_COL, how="left")
        .join(
            star["dim_opleiding"].select("Opleidingscode", "Opleidingsniveau"),
            on="Opleidingscode",
            how="left",
        )
        .with_columns(
            pl.col(STATUS_VELD)
            .str.split(STATUS_SCHEIDING)
            .list.contains(BUITEN_BEOORDELING)
            .not_()
            .fill_null(True)
            .alias("Beoordeeld")
        )
    )
    if niveaus:
        df = df.filter(pl.col("Opleidingsniveau").is_in(niveaus))
    return df


def trechter(df: pl.DataFrame) -> pl.DataFrame:
    """Aantallen per stap: in bestand → beoordeeld → bekostigd."""
    beoordeeld = df.filter(pl.col("Beoordeeld"))
    aantallen = [
        df.height,
        beoordeeld.height,
        beoordeeld.filter(pl.col("Bekostigingsindicatie")).height,
    ]
    return pl.DataFrame(
        {"Stap": list(TRECHTER_STAPPEN), "Aantal": aantallen},
        schema={"Stap": pl.Utf8, "Aantal": pl.Int64},
    )


def redenen_niet_bekostigd(df: pl.DataFrame, star: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Aantal niet-bekostigde, beoordeelde rijen per statuscode en groep."""
    niet = df.filter(pl.col("Beoordeeld") & ~pl.col("Bekostigingsindicatie")).select(FEIT_ID)
    if niet.is_empty():
        return pl.DataFrame(schema=_REDENEN_SCHEMA)
    return (
        star["fact_status"]
        .join(niet, on=FEIT_ID, how="semi")
        .join(star["dim_status"].filter(~pl.col("Bekostigd")), on="Code", how="inner")
        .group_by("Groep", "Code", "Omschrijving")
        .len("Aantal")
        .sort(["Aantal", "Code"], descending=[True, False])
        .select(list(_REDENEN_SCHEMA))
    )


def per_opleiding(df: pl.DataFrame) -> pl.DataFrame:
    """Per opleiding: aantal beoordeeld, aantal bekostigd en het aandeel."""
    return (
        df.filter(pl.col("Beoordeeld"))
        .group_by("Opleidingscode", "Opleidingsniveau")
        .agg(
            pl.len().cast(pl.Int64).alias("Totaal"),
            pl.col("Bekostigingsindicatie").sum().cast(pl.Int64).alias("Bekostigd"),
        )
        .with_columns((pl.col("Bekostigd") / pl.col("Totaal")).alias("AandeelBekostigd"))
        .sort("Opleidingscode")
    )


def _status_per_deelname(star: dict[str, pl.DataFrame], soort: str) -> pl.DataFrame:
    df = feiten(star, "fact_deelname", actuele_leveringen(star, soort))
    return df.select(*DEELNAME_SLEUTEL, pl.col(STATUS_VELD).alias(soort))


def voorlopig_vs_definitief(star: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Deelnames waarvan de status tussen voorlopig en definitief veranderde."""
    if not (heeft_soort(star, VOORLOPIG) and heeft_soort(star, DEFINITIEF)):
        return pl.DataFrame(schema=_VERSCHIL_SCHEMA)
    return (
        _status_per_deelname(star, VOORLOPIG)
        .join(_status_per_deelname(star, DEFINITIEF), on=DEELNAME_SLEUTEL, how="inner")
        .filter(pl.col(VOORLOPIG).ne_missing(pl.col(DEFINITIEF)))
        .rename({VOORLOPIG: "Voorlopig", DEFINITIEF: "Definitief"})
        .group_by("Bekostigingsjaar", "Voorlopig", "Definitief")
        .len("Aantal")
        .sort(["Bekostigingsjaar", "Aantal"], descending=[False, True])
        .select(list(_VERSCHIL_SCHEMA))
    )


def historie(star: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Per bekostigingsjaar en bron: totaal en bekostigd, uit de HISBEK-levering."""
    leveringen = actuele_leveringen(star, HISTORISCH)
    delen = [
        feiten(star, feit, leveringen).select(
            "Bekostigingsjaar", pl.lit(bron).alias("Bron"), "Bekostigingsindicatie"
        )
        for feit, bron in FEIT_BRON.items()
    ]
    return (
        pl.concat(delen)
        .group_by("Bekostigingsjaar", "Bron")
        .agg(
            pl.len().cast(pl.Int64).alias("Totaal"),
            pl.col("Bekostigingsindicatie").sum().cast(pl.Int64).alias("Bekostigd"),
        )
        .sort("Bekostigingsjaar", "Bron")
    )
```

- [ ] **Step 4: Run de tests**

Run: `uv run pytest tests/test_indicatoren.py -v`
Expected: alle tests PASS.

- [ ] **Step 5: Volledige suite, lint en commit**

```bash
uv run pytest && uv run ruff format . && uv run ruff check . && uv run ty check
git add src/ho_bekostiging_bestanden/indicatoren.py tests/test_indicatoren.py
git commit -m "feat(indicatoren): trechter, redenen, per opleiding, voorlopig/definitief, historie

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Streamlit-app — Home en Resultaten

**Files:**
- Create: `app/main.py`, `app/_utils.py`, `app/config.toml`, `app/_tabel_docs.py`, `app/pages/home.py`, `app/pages/resultaten.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `vind_bestanden`, `verwerk_alles`, `detect_levering`, `DATAMODEL_MAP` (Task 8); `parse_bestandsnaam` (Task 3); `STAR_TABELLEN` (Task 7).
- Produces:
  - `_utils.CONFIG_ENV = "HO_APP_CONFIG"`: omgevingsvariabele met een alternatief pad naar `config.toml` (voor tests en eigen data).
  - `_utils.load_config() -> dict`, `raw_dir() -> Path`, `prepared_dir() -> Path`, `output_dir() -> Path`, `datamodel_dir() -> Path`
  - `_utils.lees_star(datamodel: Path) -> dict[str, pl.DataFrame] | None`: alle `STAR_TABELLEN` als Parquet, of `None` als die (nog) niet bestaan.
  - `_tabel_docs.PAGINA_INTRO: str`, `_tabel_docs.TABEL_DOCS: dict[str, dict[str, str]]` (sleutels `titel`, `wat`, `bron`), `_tabel_docs.tabel_help(naam: str) -> None`

- [ ] **Step 1: Schrijf de falende tests `tests/test_app.py`**

```python
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ho_bekostiging_bestanden.star import STAR_TABELLEN

from .conftest import DEMO_RAW

APP = Path(__file__).parents[1] / "app"
sys.path.insert(0, str(APP))

from _tabel_docs import TABEL_DOCS  # noqa: E402
from _utils import CONFIG_ENV  # noqa: E402

TIMEOUT = 60


@pytest.fixture
def app_config(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text(
        "[data]\n"
        f'raw = "{DEMO_RAW.as_posix()}"\n'
        f'prepared = "{(tmp_path / "prep").as_posix()}"\n'
        f'output = "{(tmp_path / "out").as_posix()}"\n'
    )
    monkeypatch.setenv(CONFIG_ENV, str(config))
    return tmp_path


def _pagina(naam: str) -> AppTest:
    return AppTest.from_file(str(APP / "pages" / f"{naam}.py"), default_timeout=TIMEOUT)


def test_tabel_docs_compleet():
    assert set(TABEL_DOCS) == set(STAR_TABELLEN)
    for naam, doc in TABEL_DOCS.items():
        assert {"titel", "wat", "bron"} <= set(doc), naam


def test_home_toont_bestanden_en_verwerkt(app_config):
    at = _pagina("home").run()
    assert not at.exception
    assert at.dataframe[0].value.shape[0] == 4
    at.button(key="verwerk_alles").click().run()
    assert not at.exception
    assert at.success
    assert (app_config / "out" / "datamodel" / "fact_deelname.parquet").exists()


def test_resultaten_zonder_verwerking(app_config):
    at = _pagina("resultaten").run()
    assert not at.exception
    assert at.warning


def test_resultaten_na_verwerking(app_config):
    _pagina("home").run().button(key="verwerk_alles").click().run()
    at = _pagina("resultaten").run()
    assert not at.exception
    assert at.selectbox(key="resultaten_tabel").options[0] in STAR_TABELLEN
```

- [ ] **Step 2: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_app.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named '_tabel_docs'`

- [ ] **Step 3: Schrijf `app/config.toml`**

```toml
# Datapaden voor de Streamlit-app. Wijzen standaard naar de demo-data.
# Eigen data: zet een kopie van dit bestand elders en wijs ernaar met de
# omgevingsvariabele HO_APP_CONFIG.
[data]
raw = "data/01-raw/demo"
prepared = "data/02-prepared/demo"
output = "data/03-output/demo"
```

- [ ] **Step 4: Schrijf `app/_utils.py`**

```python
"""Gedeelde hulpfuncties voor de Streamlit-app (geen bedrijfslogica)."""

import os
import tomllib
from pathlib import Path

import polars as pl

from ho_bekostiging_bestanden.pipeline import DATAMODEL_MAP
from ho_bekostiging_bestanden.star import STAR_TABELLEN

CONFIG_ENV = "HO_APP_CONFIG"
_STANDAARD_CONFIG = Path(__file__).parent / "config.toml"


def load_config() -> dict:
    config_path = Path(os.environ.get(CONFIG_ENV, _STANDAARD_CONFIG))
    with config_path.open("rb") as f:
        return tomllib.load(f)


def raw_dir() -> Path:
    return Path(load_config()["data"]["raw"])


def prepared_dir() -> Path:
    return Path(load_config()["data"]["prepared"])


def output_dir() -> Path:
    return Path(load_config()["data"]["output"])


def datamodel_dir() -> Path:
    return output_dir() / DATAMODEL_MAP


def lees_star(datamodel: Path) -> dict[str, pl.DataFrame] | None:
    """Lees alle star-tabellen; ``None`` als het star schema nog niet bestaat."""
    paden = {naam: datamodel / f"{naam}.parquet" for naam in STAR_TABELLEN}
    if not all(p.exists() for p in paden.values()):
        return None
    return {naam: pl.read_parquet(p) for naam, p in paden.items()}
```

- [ ] **Step 5: Schrijf `app/main.py`**

```python
"""Streamlit-app entrypoint."""

import streamlit as st

st.set_page_config(
    page_title="HO-bekostigingsbestanden",
    page_icon="📊",
    layout="centered",
)

pg = st.navigation(
    [
        st.Page("pages/home.py", title="Home", default=True),
        st.Page("pages/dashboard.py", title="Dashboard"),
        st.Page("pages/resultaten.py", title="Resultaten"),
    ],
    position="sidebar",
)
pg.run()
```

`pages/dashboard.py` komt in Task 12. Maak nu alvast een placeholder zodat de navigatie werkt:

```python
"""Dashboard — wordt gevuld in Task 12."""

import streamlit as st

st.title("Dashboard")
st.info("Nog niet beschikbaar.")
```

- [ ] **Step 6: Schrijf `app/_tabel_docs.py`**

```python
"""Documentatie per tabel op de Resultaten-pagina.

Elke star-schema-tabel krijgt via :func:`tabel_help` een uitklapbaar
uitlegblok in gewone taal: wát de tabel bevat en uit welk DUO-bestand
(VLPBEK/DEFBEK/HISBEK) de gegevens komen.

Bewust géén bedrijfslogica; het model leeft in ``src/.../star.py``.
"""

import streamlit as st

PAGINA_INTRO = (
    "Op deze pagina blader je door de verwerkte tabellen (het **star schema**). "
    "Kies een tabel, bekijk de eerste 1 000 rijen en download desgewenst de "
    "volledige tabel als CSV.\n\n"
    "Een tabel kan **leeg** zijn als het bijbehorende bestand niet is verwerkt "
    "(bijvoorbeeld geen HISBEK-bestand). Dat is geen fout."
)

TABEL_DOCS: dict[str, dict[str, str]] = {
    "dim_levering": {
        "titel": "Leveringen",
        "wat": (
            "Eén regel per verwerkt bestand: soort levering (VLPBEK = voorlopig, "
            "DEFBEK = definitief, HISBEK = historisch), bekostigingsjaar, "
            "aanmaakdatum en de instelling (BRIN) die het bestand ontving."
        ),
        "bron": "Bestandsnaam en voorlooprecord (VLP) van elk bestand.",
    },
    "dim_persoon": {
        "titel": "Personen",
        "wat": (
            "Eén regel per student, met BSN en/of onderwijsnummer en de datums "
            "waarop een eerste AD-, bachelor- of mastergraad is behaald. De "
            "sleutel `_persoon_id` is het BSN, of het onderwijsnummer als er "
            "geen BSN is."
        ),
        "bron": "BLB-records (loopbaan) en de persoonsnummers in BRD/BRR/HRD/HRR.",
    },
    "dim_instelling": {
        "titel": "Instellingen",
        "wat": (
            "Alle instellingen (BRIN) waar de studenten ingeschreven stonden of "
            "een graad behaalden. `EigenInstelling` geeft aan welke BRIN de "
            "bestanden heeft ontvangen; de andere zijn instellingen waar dezelfde "
            "studenten óók stonden ingeschreven."
        ),
        "bron": "BRD/BRR/HRD/HRR en het voorlooprecord.",
    },
    "dim_opleiding": {
        "titel": "Opleidingen",
        "wat": (
            "Eén regel per opleidingscode (ISAT/CROHO) met opleidingsniveau "
            "(bijv. HBO-BA), onderdeel (bijv. TECHNIEK) en de indicaties voor de "
            "LG-sector en het academisch ziekenhuis. Opleidingsnamen zitten niet "
            "in de DUO-bestanden."
        ),
        "bron": "BRD/BRR/HRD/HRR; bij verschillen telt de nieuwste levering.",
    },
    "dim_status": {
        "titel": "Bekostigingsstatussen",
        "wat": (
            "De 34 statuscodes uit de PvE met omschrijving, een groep en of de "
            "code 'bekostigd' betekent. De groepen zijn een eigen indeling, "
            "niet van DUO."
        ),
        "bron": "PvE HO-instelling – DUO, §19.7.5.",
    },
    "fact_deelname": {
        "titel": "Deelnames (inschrijvingen)",
        "wat": (
            "Eén regel per inschrijving per levering, met bekostigingsindicatie "
            "(J/N), statuscode(s), opleidingsfase, onderwijsvorm en datums. Bevat "
            "ook inschrijvingen bij andere instellingen van dezelfde studenten."
        ),
        "bron": "BRD-records (VLPBEK/DEFBEK) en HRD-records (HISBEK).",
    },
    "fact_resultaat": {
        "titel": "Resultaten (graden)",
        "wat": (
            "Eén regel per behaalde graad per levering, met bekostigingsindicatie, "
            "statuscode, datum diploma en joint-degree-factor."
        ),
        "bron": "BRR-records (VLPBEK/DEFBEK) en HRR-records (HISBEK).",
    },
    "fact_status": {
        "titel": "Statuscodes per deelname of resultaat",
        "wat": (
            "Koppeltabel: een deelname met status `na,ti` staat hier twee keer, "
            "één keer per code. Zo kun je per reden tellen."
        ),
        "bron": "Veld CodeBekostigingstatus uit de deelnames en resultaten.",
    },
    "fact_loopbaan": {
        "titel": "Bekostigingsloopbaan",
        "wat": (
            "Per student en levering: het aantal al bekostigde inschrijfjaren "
            "(verbruik) per type opleiding. Leeg (n.v.t.) als er door een eerder "
            "behaalde graad niets meer bekostigd kan worden."
        ),
        "bron": "BLB-records; alleen in VLPBEK/DEFBEK, dus leeg met alleen HISBEK.",
    },
}


def tabel_help(naam: str) -> None:
    """Toon een uitklapbaar uitlegblok voor een star-tabel."""
    doc = TABEL_DOCS.get(naam)
    if doc is None:
        return
    with st.expander(f"ℹ️ Wat staat er in *{doc['titel']}*?"):
        st.markdown(doc["wat"])
        st.caption(f"Bron: {doc['bron']}")
```

- [ ] **Step 7: Schrijf `app/pages/home.py`**

```python
"""Home — ontdek de bestanden en verwerk ze in één stap."""

import sys
from pathlib import Path

import polars as pl
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from _utils import output_dir, prepared_dir, raw_dir

from ho_bekostiging_bestanden.ingest import parse_bestandsnaam
from ho_bekostiging_bestanden.pipeline import (
    detect_levering,
    verwerk_alles,
    vind_bestanden,
)

UPLOAD_MAP = "upload"


def _overzicht(bestanden: list[Path]) -> pl.DataFrame:
    rijen = []
    for pad in bestanden:
        info = parse_bestandsnaam(pad)
        if info is None:
            continue
        rijen.append(
            {
                "Bestand": info.bestandsnaam,
                "Soort": info.soort,
                "Bekostigingsjaar": info.bekostigingsjaar,
                "Aangemaakt": info.datum_aanmaak,
                "BRIN": info.brin,
            }
        )
    return pl.DataFrame(rijen)


def _bewaar_uploads(raw: Path) -> None:
    uploads = st.file_uploader(
        "Of voeg een los bestand toe (VLPBEK, DEFBEK of HISBEK)",
        type=["csv"],
        accept_multiple_files=True,
        key="upload",
    )
    for upload in uploads or []:
        if detect_levering(upload.name) is None:
            st.error(
                f"`{upload.name}` wordt niet herkend. Verwacht een naam als "
                "`VLPBEK_2025_20240115_99XX.csv`."
            )
            continue
        doel = raw / UPLOAD_MAP / upload.name
        doel.parent.mkdir(parents=True, exist_ok=True)
        doel.write_bytes(upload.getvalue())
        st.toast(f"{upload.name} toegevoegd")


st.markdown(
    """<style>
.hero { background: linear-gradient(135deg,#1a56db 0%,#0e3fa8 100%);
        padding: 2rem 1.5rem; border-radius: 10px; color: white;
        margin-bottom: 1.5rem; text-align: center; }
.hero h1 { margin: 0 0 .4rem 0; font-size: 2rem; font-weight: 700; }
.hero p  { margin: 0; opacity: .88; font-size: 1rem; }
</style>
<div class="hero">
  <h1>HO-bekostigingsbestanden</h1>
  <p>Zet DUO-analysebestanden (VLPBEK, DEFBEK, HISBEK) om naar een star schema.</p>
</div>""",
    unsafe_allow_html=True,
)

raw = raw_dir()
_bewaar_uploads(raw)
bestanden = vind_bestanden(raw)

if not bestanden:
    st.info(
        f"Geen herkenbare bestanden gevonden in `{raw}`. Zet VLPBEK-, DEFBEK- of "
        "HISBEK-bestanden in de invoermap of voeg ze hierboven toe."
    )
    st.stop()

st.subheader(f"{len(bestanden)} bestand(en) gevonden")
st.dataframe(_overzicht(bestanden), hide_index=True, use_container_width=True)

if st.button("Verwerk alles", type="primary", key="verwerk_alles"):
    with st.spinner("Bezig met verwerken…"):
        resultaat = verwerk_alles(raw, prepared_dir(), output_dir())
    for naam, fout in resultaat.fouten.items():
        st.error(f"**{naam}** kon niet worden verwerkt: {fout}")
    for naam, rapport in resultaat.validatie.items():
        if not rapport.is_empty():
            with st.expander(f"⚠️ {naam}: {rapport.height} controle(s) met meldingen"):
                st.dataframe(rapport, hide_index=True, use_container_width=True)
    totaal = sum(df.height for df in resultaat.star.values())
    st.success(
        f"{len(resultaat.prepared_dirs)} bestand(en) verwerkt; star schema met "
        f"{len(resultaat.star)} tabellen en {totaal:,} rijen."
    )

col_dash, col_res = st.columns(2)
with col_dash:
    if st.button("Naar het dashboard →", use_container_width=True):
        st.switch_page("pages/dashboard.py")
with col_res:
    if st.button("Naar de resultaten →", use_container_width=True):
        st.switch_page("pages/resultaten.py")
```

- [ ] **Step 8: Schrijf `app/pages/resultaten.py`**

```python
"""Resultaten — blader door de star-schema-tabellen en download ze."""

import sys
from pathlib import Path

import polars as pl
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from _tabel_docs import PAGINA_INTRO, tabel_help
from _utils import datamodel_dir

from ho_bekostiging_bestanden.star import STAR_TABELLEN

VOORBEELD_RIJEN = 1_000


@st.cache_resource(show_spinner=False)
def _lees_tabel(pad: str, mtime: float) -> pl.DataFrame:
    """Houdt een gelezen Parquet-tabel in het geheugen tussen reruns."""
    return pl.read_parquet(pad)


@st.cache_data(show_spinner=False)
def _tabel_csv(pad: str, mtime: float) -> str:
    """Maakt de CSV-tekst één keer per bestand in plaats van bij elke rerun."""
    return _lees_tabel(pad, mtime).write_csv()


st.title("Resultaten")
st.info(PAGINA_INTRO)

datamodel = datamodel_dir()
tabellen = {
    naam: datamodel / f"{naam}.parquet"
    for naam in STAR_TABELLEN
    if (datamodel / f"{naam}.parquet").exists()
}

if not tabellen:
    st.warning("Geen resultaten — verwerk eerst de bestanden op de Home-pagina.")
    if st.button("← Home"):
        st.switch_page("pages/home.py")
    st.stop()

gekozen = st.selectbox("Kies tabel", list(tabellen), key="resultaten_tabel")
if gekozen:
    pad = tabellen[gekozen]
    tabel_help(gekozen)
    mtime = pad.stat().st_mtime
    df = _lees_tabel(str(pad), mtime)

    col_rijen, col_kolommen = st.columns(2)
    col_rijen.metric("Rijen", f"{df.height:,}")
    col_kolommen.metric("Kolommen", f"{df.width:,}")

    st.dataframe(df.head(VOORBEELD_RIJEN), use_container_width=True, hide_index=True)
    if df.height > VOORBEELD_RIJEN:
        st.caption(f"Eerste {VOORBEELD_RIJEN:,} van {df.height:,} rijen getoond.")

    st.download_button(
        label=f"Download `{gekozen}.csv`",
        data=_tabel_csv(str(pad), mtime),
        file_name=f"{gekozen}.csv",
        mime="text/csv",
        use_container_width=True,
    )
```

- [ ] **Step 9: Run de tests**

Run: `uv run pytest tests/test_app.py -v`
Expected: alle tests PASS.

- [ ] **Step 10: Handmatige rooktest**

Run: `uv run streamlit run app/main.py`. Open http://localhost:8501, klik **Verwerk alles**, ga naar Resultaten, kies `fact_deelname` en download de CSV. Controleer dat de download opent en `CodeBekostigingstatus` als tekst bevat (bijv. `na,ti`). Stop de server met Ctrl+C.

- [ ] **Step 11: Lint en commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add app tests/test_app.py
git commit -m "feat(app): Home (ontdekken, uploaden, verwerken) en Resultaten

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Dashboard met grafiektoelichtingen

**Files:**
- Create: `app/_chart_docs.py`
- Modify: `app/pages/dashboard.py` (placeholder uit Task 11 vervangen)
- Test: `tests/test_dashboard.py`

**Interfaces:**
- Consumes: `indicatoren` (Task 10); `_utils.lees_star`, `_utils.datamodel_dir`, `_utils.CONFIG_ENV` (Task 11); `verwerk_alles` (Task 8).
- Produces: `_chart_docs.CHART_DOCS: dict[str, dict]` (sleutels `titel`, `variabelen: list[str]`, `manipulatie`, optioneel `kanttekening`) en `_chart_docs.chart_help(sleutel: str) -> None`. De grafieksleutels zijn `trechter`, `redenen`, `per_opleiding`, `voorlopig_definitief` en `historie`.

- [ ] **Step 1: Laad de skill `dataviz`** voordat je grafiekcode schrijft, en pas de kleur- en labelregels daaruit toe op `_hbar` hieronder. De code hieronder gebruikt Altair (wordt met Streamlit meegeïnstalleerd) met één neutrale kleur en labels in gewone taal.

- [ ] **Step 2: Schrijf de falende tests `tests/test_dashboard.py`**

```python
import re
import shutil
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ho_bekostiging_bestanden.pipeline import verwerk_alles

from .conftest import DEMO_RAW

APP = Path(__file__).parents[1] / "app"
sys.path.insert(0, str(APP))

from _chart_docs import CHART_DOCS  # noqa: E402
from _utils import CONFIG_ENV  # noqa: E402

TIMEOUT = 60


def _config(tmp_path, monkeypatch, raw: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        "[data]\n"
        f'raw = "{raw.as_posix()}"\n'
        f'prepared = "{(tmp_path / "prep").as_posix()}"\n'
        f'output = "{(tmp_path / "out").as_posix()}"\n'
    )
    monkeypatch.setenv(CONFIG_ENV, str(config))


def _dashboard() -> AppTest:
    return AppTest.from_file(str(APP / "pages" / "dashboard.py"), default_timeout=TIMEOUT)


def test_elke_grafiek_heeft_toelichting():
    bron = (APP / "pages" / "dashboard.py").read_text(encoding="utf-8")
    gebruikt = set(re.findall(r'chart_help\("(\w+)"\)', bron))
    assert gebruikt == set(CHART_DOCS)
    for sleutel, doc in CHART_DOCS.items():
        assert {"titel", "variabelen", "manipulatie"} <= set(doc), sleutel


def test_dashboard_zonder_data(tmp_path, monkeypatch):
    _config(tmp_path, monkeypatch, DEMO_RAW)
    at = _dashboard().run()
    assert not at.exception
    assert at.warning


def test_dashboard_met_demo(tmp_path, monkeypatch):
    _config(tmp_path, monkeypatch, DEMO_RAW)
    verwerk_alles(DEMO_RAW, tmp_path / "prep", tmp_path / "out")
    at = _dashboard().run()
    assert not at.exception
    assert len(at.tabs) == 5


@pytest.mark.parametrize(
    "bestand",
    ["VLPBEK_2025_20240115_99XX.csv", "HISBEK_2024_20250301_99XX.csv"],
    ids=["alleen VLPBEK", "alleen HISBEK"],
)
def test_dashboard_met_een_levering(tmp_path, monkeypatch, bestand):
    raw = tmp_path / "raw"
    raw.mkdir()
    shutil.copy(DEMO_RAW / bestand, raw / bestand)
    _config(tmp_path, monkeypatch, raw)
    verwerk_alles(raw, tmp_path / "prep", tmp_path / "out")
    at = _dashboard().run()
    assert not at.exception
    assert at.info  # uitleg bij de grafieken waarvoor data ontbreekt
```

- [ ] **Step 3: Run om te zien dat ze falen**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named '_chart_docs'`

- [ ] **Step 4: Schrijf `app/_chart_docs.py`**

```python
"""Documentatie per grafiek in het dashboard.

Elke grafiek in ``dashboard.py`` toont via :func:`chart_help` een uitklapbaar
uitlegblok: welke star-schema-variabelen gebruikt worden en, in gewone taal,
welke bewerking erachter zit. Waar iets nog bevestigd moet worden, staat dat
in de kanttekening.

Bewust géén bedrijfslogica; de berekeningen staan in ``indicatoren.py``.
"""

import streamlit as st

CHART_DOCS: dict[str, dict] = {
    "trechter": {
        "titel": "Bekostigingstrechter",
        "variabelen": [
            "fact_deelname / fact_resultaat",
            "CodeBekostigingstatus",
            "Bekostigingsindicatie",
            "dim_instelling.EigenInstelling",
        ],
        "manipulatie": (
            "Alleen rijen van de eigen instelling in de gekozen levering. "
            "**In bestand** = alle rijen. **Beoordeeld** = zonder status `mv` "
            "(inschrijving niet geldig op de peildatum; die rijen neemt DUO "
            "alleen mee voor het complete beeld). **Bekostigd** = beoordeeld én "
            "bekostigingsindicatie J."
        ),
        "kanttekening": (
            "Dat `mv` de juiste afbakening is voor 'beoordeeld' is een aanname "
            "op basis van PvE §17.5 en moet nog bevestigd worden."
        ),
    },
    "redenen": {
        "titel": "Waarom niet bekostigd?",
        "variabelen": [
            "fact_status.Code",
            "dim_status.Omschrijving",
            "dim_status.Groep",
            "Bekostigingsindicatie",
        ],
        "manipulatie": (
            "Van de beoordeelde, niet-bekostigde deelnames wordt elke statuscode "
            "apart geteld (een deelname met `na,ti` telt bij beide codes). Codes "
            "die 'bekostigd' betekenen, vallen weg."
        ),
        "kanttekening": (
            "De groepen (zoals 'Aanlevering' of 'Verbruik en limieten') zijn een "
            "eigen indeling, niet van DUO."
        ),
    },
    "per_opleiding": {
        "titel": "Aandeel bekostigd per opleiding",
        "variabelen": [
            "Opleidingscode",
            "dim_opleiding.Opleidingsniveau",
            "Bekostigingsindicatie",
        ],
        "manipulatie": (
            "Per opleidingscode: het aantal beoordeelde deelnames van de eigen "
            "instelling en het deel daarvan met bekostigingsindicatie J."
        ),
    },
    "voorlopig_definitief": {
        "titel": "Voorlopig tegenover definitief",
        "variabelen": [
            "dim_levering.SoortLevering",
            "Bekostigingsjaar",
            "BRIN",
            "Inschrijvingvolgnummer",
            "_persoon_id",
            "CodeBekostigingstatus",
        ],
        "manipulatie": (
            "Per bekostigingsjaar wordt de nieuwste VLPBEK naast de nieuwste "
            "DEFBEK gelegd. Deelnames worden gekoppeld op jaar, BRIN, "
            "inschrijvingvolgnummer en persoon; getoond worden alleen de "
            "deelnames waarvan de statuscode veranderde."
        ),
    },
    "historie": {
        "titel": "Bekostiging per jaar (historisch)",
        "variabelen": [
            "dim_levering.SoortLevering = HISBEK",
            "Bekostigingsjaar",
            "Bekostigingsindicatie",
        ],
        "manipulatie": (
            "Uit het HISBEK-bestand: per bekostigingsjaar het aantal deelnames en "
            "graden van de eigen instelling en hoeveel daarvan bekostigd zijn."
        ),
        "kanttekening": "Alleen zichtbaar als er een HISBEK-bestand is verwerkt.",
    },
}


def chart_help(sleutel: str) -> None:
    """Toon een uitklapbaar uitlegblok voor een grafiek."""
    doc = CHART_DOCS[sleutel]
    with st.expander(f"ℹ️ Toelichting: {doc['titel']}"):
        st.markdown(doc["manipulatie"])
        st.caption("Variabelen: " + ", ".join(f"`{v}`" for v in doc["variabelen"]))
        if "kanttekening" in doc:
            st.warning(doc["kanttekening"])
```

- [ ] **Step 5: Schrijf `app/pages/dashboard.py`**

```python
"""Dashboard — bekostiging van de eigen instelling in vijf tabs."""

import sys
from pathlib import Path

import altair as alt
import polars as pl
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from _chart_docs import chart_help
from _utils import datamodel_dir, lees_star

from ho_bekostiging_bestanden import indicatoren as ind

LEVERING_LABELS = {ind.DEFINITIEF: "Definitief (DEFBEK)", ind.VOORLOPIG: "Voorlopig (VLPBEK)"}
BALK_KLEUR = "#1a56db"
BALK_HOOGTE = 28  # pixels per balk


@st.cache_data(show_spinner=False)
def _star(pad: str, mtime: float) -> dict[str, pl.DataFrame] | None:
    return lees_star(Path(pad))


def _mtime(pad: Path) -> float:
    return max((p.stat().st_mtime for p in pad.glob("*.parquet")), default=0.0)


def _hbar(df: pl.DataFrame, label: str, waarde: str, formaat: str = ",d") -> None:
    """Horizontale balken in de volgorde van ``df``."""
    grafiek = (
        alt.Chart(df.to_pandas())
        .mark_bar(color=BALK_KLEUR)
        .encode(
            x=alt.X(waarde, title=None, axis=alt.Axis(format=formaat)),
            y=alt.Y(label, title=None, sort=None),
            tooltip=[label, alt.Tooltip(waarde, format=formaat)],
        )
        .properties(height=max(BALK_HOOGTE * df.height, BALK_HOOGTE * 2))
    )
    st.altair_chart(grafiek, use_container_width=True)


def _tab_trechter(deelnames: pl.DataFrame, resultaten: pl.DataFrame) -> None:
    chart_help("trechter")
    for titel, df in (("Deelnames", deelnames), ("Graden", resultaten)):
        st.markdown(f"**{titel}**")
        _hbar(ind.trechter(df), "Stap", "Aantal")


def _tab_redenen(deelnames: pl.DataFrame, star: dict[str, pl.DataFrame]) -> None:
    chart_help("redenen")
    redenen = ind.redenen_niet_bekostigd(deelnames, star)
    if redenen.is_empty():
        st.info("Alle beoordeelde deelnames in deze selectie zijn bekostigd.")
        return
    _hbar(redenen, "Omschrijving", "Aantal")
    st.dataframe(redenen, hide_index=True, use_container_width=True)


def _tab_opleiding(deelnames: pl.DataFrame) -> None:
    chart_help("per_opleiding")
    per_opl = ind.per_opleiding(deelnames)
    if per_opl.is_empty():
        st.info("Geen beoordeelde deelnames in deze selectie.")
        return
    per_opl = per_opl.with_columns(
        pl.format("{} ({})", "Opleidingscode", "Opleidingsniveau").alias("Opleiding")
    ).sort("AandeelBekostigd")
    _hbar(per_opl, "Opleiding", "AandeelBekostigd", formaat=".0%")
    st.dataframe(per_opl.drop("Opleiding"), hide_index=True, use_container_width=True)


def _tab_voorlopig_definitief(star: dict[str, pl.DataFrame]) -> None:
    chart_help("voorlopig_definitief")
    if not (ind.heeft_soort(star, ind.VOORLOPIG) and ind.heeft_soort(star, ind.DEFINITIEF)):
        st.info("Verwerk een VLPBEK- én een DEFBEK-bestand van hetzelfde jaar om te vergelijken.")
        return
    verschil = ind.voorlopig_vs_definitief(star)
    if verschil.is_empty():
        st.info("Geen statuswijzigingen tussen voorlopig en definitief.")
        return
    verschil = verschil.with_columns(
        pl.format("{}: {} → {}", "Bekostigingsjaar", "Voorlopig", "Definitief").alias("Wijziging")
    )
    _hbar(verschil, "Wijziging", "Aantal")


def _tab_historie(star: dict[str, pl.DataFrame]) -> None:
    chart_help("historie")
    if not ind.heeft_soort(star, ind.HISTORISCH):
        st.info("Verwerk een HISBEK-bestand om de bekostiging over meerdere jaren te zien.")
        return
    hist = ind.historie(star).with_columns(
        (pl.col("Bekostigd") / pl.col("Totaal")).alias("AandeelBekostigd")
    )
    grafiek = (
        alt.Chart(hist.to_pandas())
        .mark_line(point=True, color=BALK_KLEUR)
        .encode(
            x=alt.X("Bekostigingsjaar:O", title="Bekostigingsjaar"),
            y=alt.Y("AandeelBekostigd:Q", title="Aandeel bekostigd", axis=alt.Axis(format=".0%")),
            strokeDash=alt.StrokeDash("Bron:N", title=None),
            tooltip=["Bekostigingsjaar", "Bron", "Totaal", "Bekostigd",
                     alt.Tooltip("AandeelBekostigd", format=".0%")],
        )
    )
    st.altair_chart(grafiek, use_container_width=True)
    st.dataframe(hist, hide_index=True, use_container_width=True)


st.title("Dashboard")

datamodel = datamodel_dir()
star = _star(str(datamodel), _mtime(datamodel))
if star is None:
    st.warning("Nog geen star schema — verwerk eerst de bestanden op de Home-pagina.")
    st.stop()

soorten = [s for s in LEVERING_LABELS if ind.heeft_soort(star, s)]
deelnames = ind.feiten(star, "fact_deelname", [])
resultaten = ind.feiten(star, "fact_resultaat", [])
if soorten:
    soort = st.sidebar.radio("Levering", soorten, format_func=LEVERING_LABELS.get)
    leveringen = ind.actuele_leveringen(star, soort)
    jaar_per_levering = dict(
        star["dim_levering"]
        .filter(pl.col("levering").is_in(leveringen))
        .select("Bekostigingsjaar", "levering")
        .rows()
    )
    jaar = st.sidebar.selectbox("Bekostigingsjaar", sorted(jaar_per_levering, reverse=True))
    niveaus = st.sidebar.multiselect(
        "Opleidingsniveau",
        sorted(star["dim_opleiding"]["Opleidingsniveau"].drop_nulls().unique()),
    )
    gekozen = [jaar_per_levering[jaar]]
    deelnames = ind.feiten(star, "fact_deelname", gekozen, niveaus)
    resultaten = ind.feiten(star, "fact_resultaat", gekozen, niveaus)
else:
    st.info("Er is alleen historische data (HISBEK); zie het tabblad Historie.")

tabs = st.tabs(["Trechter", "Waarom niet bekostigd", "Per opleiding",
                "Voorlopig vs definitief", "Historie"])
with tabs[0]:
    _tab_trechter(deelnames, resultaten)
with tabs[1]:
    _tab_redenen(deelnames, star)
with tabs[2]:
    _tab_opleiding(deelnames)
with tabs[3]:
    _tab_voorlopig_definitief(star)
with tabs[4]:
    _tab_historie(star)
```

- [ ] **Step 6: Run de tests**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: alle tests PASS.

- [ ] **Step 7: Handmatige controle in de browser**

Run: `uv run streamlit run app/main.py`. Klik op Home **Verwerk alles** en open daarna het Dashboard. Controleer:
- alle vijf tabs tonen een grafiek;
- wisselen tussen Definitief en Voorlopig verandert de trechter;
- een filter op opleidingsniveau werkt;
- elke grafiek heeft een uitklapbare toelichting.

Stop de server met Ctrl+C.

- [ ] **Step 8: Lint en commit**

```bash
uv run ruff format . && uv run ruff check . && uv run ty check
git add app tests/test_dashboard.py
git commit -m "feat(app): dashboard met trechter, redenen, opleidingen, VLP/DEF en historie

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: README en eindcontrole

**Files:**
- Create: `README.md`
- Test: de volledige suite, lint, typecheck en een handmatige run

**Interfaces:**
- Consumes: alles hierboven.
- Produces: een README die het MBO-README volgt (Context, Quick start, stappen, CLI, datamodel, vervolg, bronnen).

- [ ] **Step 1: Schrijf `README.md`**

````markdown
# ho-bekostiging-bestanden

Leest DUO HO-bekostigingsbestanden in en zet ze om naar schone, onderzoeksklare data.

## Context

Hogescholen en universiteiten kunnen bij DUO een analysebestand opvragen: voorlopig
(VLPBEK), definitief (DEFBEK) en historisch (HISBEK). Daarin staat per inschrijving
en per graad of die bekostigd wordt, en zo niet, waarom niet. De bestanden zijn ruw
(`|`-gescheiden, meerdere recordsoorten, geen kopregel). Deze repo leest ze in,
decodeert en controleert ze, en maakt er een star schema van waarop andere
CEDA-projecten kunnen voortbouwen.

Dit is de HO-tegenhanger van
[mbo-bekostiging-bestanden](https://github.com/cedanl/mbo-bekostiging-bestanden).

Doelgroep: analisten en onderzoekers bij HO-instellingen die met bekostigingsdata werken.

## Quick start

```bash
uv sync
uv run streamlit run app/main.py
```

De repo bevat synthetische demo-data, zodat alles direct werkt zonder eigen bestanden.

### Stap 1 — Bestanden verwerken

Open de app, bekijk de gevonden bestanden en klik **Verwerk alles**. Je kunt ook een
los bestand toevoegen. Per bestand zie je de uitkomst van de controles (bijvoorbeeld
of de tellingen in het sluitrecord kloppen).

### Stap 2 — Dashboard

Vijf tabs: bekostigingstrechter, waarom niet bekostigd, aandeel bekostigd per
opleiding, voorlopig tegenover definitief en historie (alleen met HISBEK). Elke grafiek
heeft een toelichting.

### Stap 3 — Resultaten

Kies een tabel uit het star schema, bekijk de eerste 1 000 rijen en download de hele
tabel als CSV.

## Eigen data

Zet je bestanden in een eigen map (bijvoorbeeld `data/01-raw/eigen/`; alles buiten
`demo/` wordt door git genegeerd) en wijs de app ernaar met een eigen `config.toml`:

```bash
HO_APP_CONFIG=pad/naar/config.toml uv run streamlit run app/main.py
```

Welke bestanden je hebt, maakt niet uit: het werkt met elke combinatie van VLPBEK,
DEFBEK en HISBEK, ook zonder HISBEK.

## CLI

```bash
# Verwerk één ruw bestand naar prepared
uv run ho verwerk data/01-raw/demo/VLPBEK_2025_20240115_99XX.csv \
    data/02-prepared/demo/VLPBEK_2025_20240115_99XX

# Bouw het star schema vanuit een of meer prepared-mappen
uv run ho star data/02-prepared/demo/* --output data/03-output/demo
```

## Datamodel

| Tabel | Eén rij per |
|---|---|
| `dim_levering` | verwerkt bestand |
| `dim_persoon` | student (`_persoon_id` = BSN, anders onderwijsnummer) |
| `dim_instelling` | BRIN (`EigenInstelling` = ontvanger van het bestand) |
| `dim_opleiding` | opleidingscode |
| `dim_status` | bekostigingsstatuscode (34 uit de PvE) |
| `fact_deelname` | inschrijving × levering (BRD + HRD) |
| `fact_resultaat` | graad × levering (BRR + HRR) |
| `fact_status` | statuscode × deelname of resultaat |
| `fact_loopbaan` | student × levering (BLB) |

## Ontwikkelen

```bash
uv run pytest            # tests
uv run ruff check .      # lint
uv run ty check          # types
uv run python scripts/genereer_demo.py   # demo-data opnieuw maken
```

Ontwerp en plan: `docs/superpowers/specs/` en `docs/superpowers/plans/`.

## Nog te bevestigen

Een aantal inhoudelijke keuzes zijn aannames. Ze staan gemarkeerd als **[Te checken]**
in de ontwerp-spec, onder andere:
- de groepsindeling van de statuscodes (eigen indeling, niet van DUO);
- `mv` als afbakening van "beoordeeld" in de trechter;
- of de oude BLB-versie (`_OUD`, tot 2019) nog voorkomt.

## Vervolg

- Overige HO-bestanden: OBO, verschillenlijst, registratieoverzicht, landelijk overzicht.
- Wisselstroom en rendement uit HISBEK (zie `cedanl/wisselstroom`).
- Opleidings- en instellingsnamen via RIO (`cedanl/rio-onderwijsdata`).
- Een gedeelde MBO/HO-kernbibliotheek.

## Bron

Programma van Eisen HO-instelling – DUO, versie 26.3.1 (17-07-2026), bijlage 8
(analysebestand) en bijlage 10 (historische bekostiging).

## Licentie

MIT
````

- [ ] **Step 2: Volledige controle**

Run: `uv sync && uv run pytest -v && uv run ruff check . && uv run ruff format --check . && uv run ty check`
Expected: alle tests PASS; ruff en ty zonder fouten.

- [ ] **Step 3: CLI van begin tot eind**

```bash
uv run ho verwerk data/01-raw/demo/VLPBEK_2025_20240115_99XX.csv data/02-prepared/demo/VLPBEK_2025_20240115_99XX
uv run ho verwerk data/01-raw/demo/HISBEK_2024_20250301_99XX.csv data/02-prepared/demo/HISBEK_2024_20250301_99XX
uv run ho star data/02-prepared/demo/VLPBEK_2025_20240115_99XX data/02-prepared/demo/HISBEK_2024_20250301_99XX --output data/03-output/demo
```

Expected: twee regels `Verwerkt: …` en één regel `Star schema gebouwd: 9 tabellen, … rijen`.

- [ ] **Step 4: Controleer dat er geen gegenereerde data wordt gecommit**

Run: `git status --porcelain data/`
Expected: geen uitvoer (prepared en output staan in `.gitignore`).

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: README met quick start, CLI, datamodel en open punten

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
