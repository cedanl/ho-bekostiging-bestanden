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

## Huisstijl

De app gebruikt de Npuls-huisstijl uit de skill `vormgever-npuls-huisstijl` in
[cedanl/.github](https://github.com/cedanl/.github). De design tokens staan in
`app/huisstijl/design-tokens.json`; kleuren, grafiekpalet en CSS komen uit
`app/_huisstijl.py`, en het Streamlit-thema in `.streamlit/config.toml` wordt in de
tests tegen de tokens gecontroleerd.

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
