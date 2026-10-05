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
- **Documentatie bijhouden** — wijzig je een schema (`metadata/*.toml`), codelijst of star-tabel: werk de pagina's in `docs/` bij. `tests/test_docs.py` faalt als ze uit de pas lopen.
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
│   ├── pipeline.py  stack.py  star.py  contracten.py  kwaliteit.py
│   ├── indicatoren.py  pseudonimisering.py  cli.py  demo.py
│   └── metadata/              # Veldindelingen (TOML) en codelijsten (CSV)
├── app/                       # Streamlit (geen bedrijfslogica)
├── docs/                      # MkDocs-documentatie (zie mkdocs.yml)
└── tests/
```

## How to Run
- Dependencies: `uv sync`
- Tests: `uv run pytest`
- App: `uv run streamlit run app/main.py`
- Docs: `uv sync --group docs` en `uv run mkdocs serve` (CI bouwt met `--strict`)
- CLI: `uv run ho verwerk <bestand> <doelmap>` en `uv run ho star <mappen…> --output <map>`

## Releases
Alleen via een tag op `main`; `.github/workflows/release.yml` is de gate
(gelijk aan mbo-bekostiging-bestanden).
1. PR die `version` in `pyproject.toml` ophoogt en `release-notes/vX.Y.Z.md`
   toevoegt → merge naar `main`.
2. Wacht tot CI en Docs op `main` groen zijn.
3. `git fetch && git tag vX.Y.Z origin/main && git push origin vX.Y.Z`.

De workflow controleert dat de tag op `main` staat, gelijk is aan de
pyproject-versie en dat CI én Docs voor die commit groen zijn, en maakt dan de
GitHub Release. Notes komen uit `release-notes/<tag>.md` (eerste regel
`# Titel` wordt de release-titel, de rest de body) en anders uit de gemergde
PR's. In beide gevallen faalt de gate als een `#NNN` in de notes niet bestaat,
of als een issue dat een PR in de notes sluit nog openstaat
(`scripts/controleer_release_notes.py`).
**Nooit** zelf `gh release create` draaien of release-notes buiten de gate om
publiceren — dat omzeilt de controle.

Een gepubliceerde release is een historisch feit. Een correctie komt als
**toevoeging met datum** bovenaan; de oorspronkelijke tekst blijft staan
(ingeklapt in `<details>`). Een inhoudelijke correctie hoort in de volgende
release ("Supersedes vX.Y.Z").

## Data
- **Input**: DUO-analysebestanden `VLPBEK_JJJJ_EEJJMMDD_99XX.CSV`, `DEFBEK_…`, `HISBEK_…`.
  Multi-record, `|`-gescheiden (VLP/BLB/BRD/BRR/SLR, resp. VLP/HRD/HRR/SLR).
  Bron: PvE HO-instelling – DUO v26.3.1, bijlagen 8 en 10.
- **Output**: Parquet in `data/02-prepared/` en star schema in `data/03-output/`.
- Echte data is gitignored; alleen synthetische demo-data in `data/01-raw/demo/`.
- Privacy: geen persoonsgegevens committen. BSN en onderwijsnummer worden direct
  na het inlezen gepseudonimiseerd, identiek aan 1cijferho (`pseudonimisering.py`,
  sleutel `EENCIJFERHO_ENCRYPT_KEY`); wijzig het algoritme nooit zonder 1cijferho
  mee te nemen, anders breekt de koppeling met 1CHO.
