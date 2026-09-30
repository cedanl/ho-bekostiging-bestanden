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

## Pseudonimisering en koppelen met 1CHO

Het BSN en het onderwijsnummer worden direct na het inlezen gepseudonimiseerd, met
precies hetzelfde algoritme als [1cijferho](https://github.com/cedanl/1cijferho)
(`pseudonymize_value`: HMAC-SHA256 met de sleutel uit `EENCIJFERHO_ENCRYPT_KEY`,
minimaal 64 bytes). In de prepared- en star-tabellen staat daardoor geen leesbaar
BSN meer.

Gebruik je in beide tools **dezelfde sleutel**, dan geeft een student in beide
hetzelfde pseudoniem. Je koppelt dan het gepseudonimiseerde 1CHO-bestand aan
`dim_persoon` op de kolom `Burgerservicenummer`, en via `_persoon_id` door naar de
feittabellen:

```python
import polars as pl

ev = pl.read_csv("EV…csv", separator=";", infer_schema_length=0)  # na 1cijferho
persoon = pl.read_parquet("data/03-output/…/datamodel/dim_persoon.parquet")
gekoppeld = ev.join(persoon, on="Burgerservicenummer", how="inner")
```

- Pseudonimisering staat **standaard aan**. Zonder sleutel verwerkt de CLI dan niets
  (`ho verwerk … --sleutelbestand <pad>` kan ook).
- Uitzetten kan expliciet: `ho verwerk … --geen-pseudonimisering`, of het vinkje op
  Home uitzetten. BSN en onderwijsnummer blijven dan leesbaar; koppelen met
  gepseudonimiseerde 1CHO-data kan dan niet. De keuze staat per levering in
  `dim_levering.Gepseudonimiseerd`, en het star schema weigert een mix van beide.
- De demo-app gebruikt een openbare demo-sleutel uit `app/config.toml` en waarschuwt
  daarvoor. Zet voor echte data altijd `EENCIJFERHO_ENCRYPT_KEY`; die gaat voor.
- Het BSN wordt gepseudonimiseerd zoals het in het bestand staat (9 tekens, met
  voorloopnul), net als in 1cijferho.
- Iemand zonder BSN (alleen een onderwijsnummer) koppelt alleen als 1CHO
  hetzelfde onderwijsnummer heeft (kolom `Onderwijsnummer`).

## Eigen data

Zet je bestanden in een eigen map (bijvoorbeeld `data/01-raw/eigen/`; alles buiten
`demo/` wordt door git genegeerd) en wijs de app ernaar met een eigen `config.toml`:

```bash
# bash / macOS / Linux
HO_APP_CONFIG=pad/naar/config.toml uv run streamlit run app/main.py
```

```powershell
# Windows PowerShell
$env:HO_APP_CONFIG = "pad\naar\config.toml"; uv run streamlit run app/main.py
```

Relatieve paden in `config.toml` gaan uit van de repo-map, dus de app werkt ook
als je hem vanuit een andere map start.

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

In Windows PowerShell werkt `*` niet als argument; geef de mappen dan zo mee:

```powershell
uv run ho star (Get-ChildItem data/02-prepared/demo -Directory).FullName --output data/03-output/demo
```

### Kwaliteit en exitcodes

Elke controle levert een melding met een ernst: `error` of `warning`. Eén
error zet de status op `fail`. De uitvoer wordt altijd geschreven, zodat je
de oorzaak kunt nalezen: per levering in de tabel `VALIDATIE`, en voor het
geheel in `<output>/quality.json`. Dat bestand bevat de status, alle
meldingen per levering en voor het star schema, de sha256 van elk
bronbestand, het aantal rijen per levering × recordsoort en de pakketversie
(schema: `src/ho_bekostiging_bestanden/metadata/quality.schema.json`).

| Exitcode | Betekenis |
|---|---|
| 0 | Klaar; status `ok` of `warn` |
| 1 | Invoerfout (onbekend bestand, geen VLP, geen sleutel) |
| 3 | Kwaliteitsstatus `fail` |

Met `--allow-quality-errors` (bij `verwerk` en `star`) geeft een `fail`
exitcode 0 en een regel "Let op: kwaliteitsstatus fail". De app toont de
status op Home en als banner op Dashboard en Resultaten.

## Datamodel

| Tabel | Eén rij per |
|---|---|
| `dim_levering` | verwerkt bestand (met `Sha256` van het bronbestand) |
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
