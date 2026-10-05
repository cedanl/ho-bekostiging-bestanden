# Release-blokkers v0.1.0 — plan

Spec: `docs/superpowers/specs/2026-10-05-release-blokkers-design.md`.
Elke stap: test schrijven → zien falen → minimale code → hele suite groen.

## Taak 1 — `_maak_leeg` ruimt alleen eigen tabellen op
1. `tests/test_pipeline.py`:
   - `test_eigen_bestand_in_doelmap_blijft_staan` — `eigen.parquet` en
     `notities.csv` in `target`; na `run_pipeline` bestaan ze nog. (rood)
   - `test_verouderde_recordsoort_wordt_opgeruimd` — `BLB.parquet` uit een
     eerdere run verdwijnt als de nieuwe levering geen BLB heeft. (borgt
     bestaand gedrag)
2. `pipeline.py`: `_pipeline_tabellen()` uit de schema's plus `LEVERING` en
   `VALIDATIE`; `_maak_leeg` verwijdert alleen die namen.

## Taak 2 — demo-sleutel alleen voor demo-data
1. `tests/test_demo.py`: `is_demo_bestand` voor demo-bestand, andere BRIN in
   naam, andere BRIN in VLP. (rood: functie bestaat niet)
2. `demo.py`: `is_demo_bestand(pad)` — BRIN uit de naam en uit de eerste regel.
3. `tests/test_app.py`: home met demo-sleutel en een niet-demo-bestand → knop
   uit, foutmelding noemt het bestand; met env-var → verwerkt. (rood)
4. `app/_utils.py`: `pseudonimiseringssleutel(bestanden)`; `home.py` geeft
   de gevonden bestanden mee.

## Taak 3 — docs en afronding
1. `docs/aan-de-slag.md` en `docs/ontwerpkeuzes.md` bijwerken.
2. `uv run pytest`, `ruff check`, `ruff format --check`, `ty check`,
   `mkdocs build --strict`.
3. Concept `release-notes/v0.1.0.md`.
