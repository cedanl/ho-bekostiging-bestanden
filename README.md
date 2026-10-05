# ho-bekostiging-bestanden

Leest DUO HO-bekostigingsbestanden in en zet ze om naar schone, onderzoeksklare data.

https://github.com/user-attachments/assets/9e2d128d-70da-4689-acc9-d22efbaf1c94

## Context

Hogescholen en universiteiten kunnen bij DUO een analysebestand opvragen: voorlopig
(VLPBEK), definitief (DEFBEK) en historisch (HISBEK). Daarin staat per inschrijving
en per graad of die bekostigd wordt, en zo niet, waarom niet. De bestanden zijn ruw:
`|`-gescheiden, meerdere recordsoorten door elkaar en geen kopregel. Deze repo leest
ze in, decodeert de velden en controleert de kwaliteit. Dat levert twee producten op:

- **Brondata per levering** (`data/02-prepared/`): elk DUO-bestand als Parquet per
  recordsoort, getrouw aan de levering en alleen getypeerd.
- **Analysemodel** (`data/03-output/…/datamodel/`): een star schema (dimensies +
  feiten) waarin de leveringen zijn samengevoegd.

Andere CEDA-projecten kunnen op beide voortbouwen.

Dit is de HO-tegenhanger van
[mbo-bekostiging-bestanden](https://github.com/cedanl/mbo-bekostiging-bestanden).

Doelgroep: analisten en onderzoekers bij HO-instellingen die met bekostigingsdata werken.

## Quick start

```bash
uv sync
uv run streamlit run app/main.py
```

De repo bevat synthetische demo-data, zodat alles direct werkt zonder eigen bestanden.

> **Privacy:** in de uitvoer staan geen leesbare BSN's of onderwijsnummers. Zie
> [Persoonsgegevens en privacy](#persoonsgegevens-en-privacy) voor wat dat voor jou
> betekent, vooral als je met echte data werkt.

### Stap 1 — Bestanden verwerken

Open de app, bekijk de gevonden bestanden en klik **Verwerk alles**. Je kunt ook een
los bestand toevoegen. Per bestand zie je de uitkomst van de controles (bijvoorbeeld
of de tellingen in het sluitrecord kloppen). Het analysemodel wordt daarna uit alle
verwerkte bestanden samen gebouwd.

### Stap 2 — Dashboard

Vijf tabs: bekostigingstrechter, waarom niet bekostigd, aandeel bekostigd per
opleiding, voorlopig tegenover definitief en historie (alleen met HISBEK). Elke grafiek
heeft een toelichting.

### Stap 3 — Resultaten

Kies een tabel uit het star schema, bekijk de eerste 1 000 rijen en download de hele
tabel als CSV.

## Eigen data verwerken

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
als je hem vanuit een andere map start. Welke bestanden je hebt, maakt niet uit: het
werkt met elke combinatie van VLPBEK, DEFBEK en HISBEK, ook zonder HISBEK.

Voor echte data heb je ook een sleutel nodig, zie het volgende hoofdstuk.

## Persoonsgegevens en privacy

De DUO-bestanden bevatten het BSN en het onderwijsnummer van studenten. Die willen
we niet leesbaar doorgeven aan analyses en dashboards. Daarom vervangt deze tool ze
meteen bij het inlezen door een **pseudoniem**: een vaste code die er willekeurig
uitziet, bijvoorbeeld `a3f9c2…`. Dezelfde student krijgt altijd dezelfde code, dus je
kunt nog steeds tellen, groeperen en studenten door de bestanden heen volgen. Maar
uit de code is het BSN niet meer terug te rekenen.

**De sleutel.** Om de code te maken gebruikt de tool een geheime sleutel (een lange
tekst, zoals een wachtwoord). Met een andere sleutel ontstaan andere codes. Dat
heeft twee gevolgen:

- Verwerk je bestanden van verschillende momenten, gebruik dan **steeds dezelfde
  sleutel**. Anders herken je dezelfde student niet meer terug.
- Bewaar de sleutel veilig en **nooit in git**. Wie de sleutel heeft, kan codes
  namaken voor bekende BSN's.

**Zo stel je de sleutel in** (minimaal 64 tekens), als omgevingsvariabele
`EENCIJFERHO_ENCRYPT_KEY`:

```bash
# bash / macOS / Linux
export EENCIJFERHO_ENCRYPT_KEY="<jouw lange geheime tekst>"
```

```powershell
# Windows PowerShell
$env:EENCIJFERHO_ENCRYPT_KEY = "<jouw lange geheime tekst>"
```

Via de CLI kan het ook met `ho verwerk … --sleutelbestand <pad>`.

**Demo-data.** De demo-app gebruikt een openbare demo-sleutel uit `app/config.toml`
en laat daarbij een waarschuwing zien. Gebruik die sleutel nooit voor echte data; een
ingestelde `EENCIJFERHO_ENCRYPT_KEY` gaat altijd voor.

**Zonder pseudonimisering.** Standaard staat pseudonimisering aan, en zonder sleutel
verwerkt de CLI niets. Uitzetten kan bewust met `ho verwerk … --geen-pseudonimisering`
(of het vinkje op Home). BSN en onderwijsnummer blijven dan leesbaar. Gebruik dat
alleen in een afgeschermde omgeving. De keuze staat per levering in
`dim_levering.Gepseudonimiseerd`; het star schema weigert een mix van beide.

### Koppelen met 1CHO-data

Gebruik je in [1cijferho](https://github.com/cedanl/1cijferho) **dezelfde sleutel**,
dan krijgt een student in beide tools dezelfde code. Je kunt de bestanden dan aan
elkaar koppelen op de kolom `Burgerservicenummer`, zonder dat iemand een echt BSN
hoeft te zien:

```python
import polars as pl

ev = pl.read_csv("EV…csv", separator=";", infer_schema_length=0)  # na 1cijferho
persoon = pl.read_parquet("data/03-output/…/datamodel/dim_persoon.parquet")
gekoppeld = ev.join(persoon, on="Burgerservicenummer", how="inner")
```

Via `_persoon_id` koppel je vervolgens door naar de feittabellen.

Goed om te weten:

- Het algoritme is identiek aan dat van 1cijferho. Pas het daarom nooit aan zonder
  1cijferho mee te nemen, anders breekt de koppeling.
- Iemand zonder BSN (alleen een onderwijsnummer) koppelt alleen als 1CHO hetzelfde
  onderwijsnummer heeft (kolom `Onderwijsnummer`).

<details>
<summary>Technische details</summary>

Het pseudoniem is een HMAC-SHA256 van de waarde met de sleutel
(`pseudonymize_value` in `pseudonimisering.py`). Het BSN wordt gehasht zoals het in
het bestand staat (9 tekens, met voorloopnul), net als in 1cijferho.

</details>

> **Alleen lokaal gebruiken:** de app is bedoeld als lokale analysetool. Er is geen
> login of rechtenbeheer: wie de app draait, kan alle tabellen downloaden.

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

## Data

- **Input**: ruwe bestanden in `data/01-raw/`: `VLPBEK_*`, `DEFBEK_*` en `HISBEK_*`.
- **Prepared**: Parquet per recordsoort in `data/02-prepared/`, één submap per levering.
- **Output**: star-schema-tabellen in `data/03-output/…/datamodel/` (zie hieronder).
- Echte data staat niet in git; alleen synthetische demo-data in `data/01-raw/demo/`.

### Datamodel

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

## Ontwikkeling

```bash
uv run pytest            # tests
uv run ruff check .      # lint
uv run ty check          # types
uv run python scripts/genereer_demo.py   # demo-data opnieuw maken
```

Open de repo in de devcontainer (VS Code / GitHub Codespaces) voor een kant-en-klare
omgeving. Ontwerp en plan: `docs/superpowers/specs/` en `docs/superpowers/plans/`.

### Huisstijl

De app gebruikt de Npuls-huisstijl uit de skill `vormgever-npuls-huisstijl` in
[cedanl/.github](https://github.com/cedanl/.github). De design tokens staan in
`app/huisstijl/design-tokens.json`; kleuren, grafiekpalet en CSS komen uit
`app/_huisstijl.py`, en het Streamlit-thema in `.streamlit/config.toml` wordt in de
tests tegen de tokens gecontroleerd.

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

## Referenties

- Bron: Programma van Eisen HO-instelling – DUO, versie 26.3.1 (17-07-2026), bijlage 8
  (analysebestand) en bijlage 10 (historische bekostiging).
- Technische context: [`CLAUDE.md`](CLAUDE.md)
- CEDA-standaarden: https://github.com/cedanl/.github/tree/main/standards/README.md

## Contact

Onderhouden door CEDA (cedanl). Bijdragen via issues en pull requests.

## Licentie

MIT
