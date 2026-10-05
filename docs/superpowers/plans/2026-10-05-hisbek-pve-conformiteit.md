# Plan: HISBEK-conformiteit met de PvE

Spec: `docs/superpowers/specs/2026-10-05-hisbek-pve-conformiteit-design.md`.
Elke taak via TDD: eerst een falende test, dan de minimale wijziging.

1. **PvE-veldindeling vastleggen** — `tests/test_pve_hisbek.py` met de
   uitgeschreven veldvolgorde van HRD/HRR uit §19.7.2/§19.7.3. (Regressietest;
   hoort direct te slagen, want de volgorde klopt al.)
2. **Verplichte velden** — test dat `required_fields` gelijk is aan de
   PvE-kolom "Verplicht = ja" (faalt) → `hisbek_schema.toml` aanpassen. Testdata
   in `tests/conftest.py` (`hisbek_regels`) bijwerken als die verplichte velden
   leeg laat.
3. **Codelijst inschrijvingsvorm** — test dat een HRD met `A` en `T` geen
   codelijstmelding geeft en een BRD met `A` wel (faalt) →
   `inschrijvingsvorm_hisbek.csv` + koppeling in `[HRD.codelijsten]`.
4. **Demo realistisch** — tests op de gegenereerde HISBEK: ECTS leeg,
   woonplaatsvereiste/Duitse deelstaat leeg buiten 2011–2014, per persoon
   aflopend op jaar (falen) → `demo.py` aanpassen, demo opnieuw genereren.
5. **Verifiëren** — volledige `uv run pytest`, `ruff check`, `ruff format
   --check`, `ty check`.
