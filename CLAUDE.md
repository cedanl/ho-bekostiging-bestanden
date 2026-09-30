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
│   ├── pipeline.py  stack.py  star.py  indicatoren.py  cli.py  demo.py
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
- Privacy: geen persoonsgegevens committen. BSN en onderwijsnummer worden direct
  na het inlezen gepseudonimiseerd, identiek aan 1cijferho (`pseudonimisering.py`,
  sleutel `EENCIJFERHO_ENCRYPT_KEY`); wijzig het algoritme nooit zonder 1cijferho
  mee te nemen, anders breekt de koppeling met 1CHO.
