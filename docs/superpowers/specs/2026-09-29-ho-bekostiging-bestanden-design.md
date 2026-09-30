# Ontwerp: ho-bekostiging-bestanden (v1)

*Datum: 2026-09-29 · Status: goedgekeurd ontwerp, klaar voor implementatieplan*

## 1. Doel

Een ingestion-repo voor **cedanl** die de DUO-bekostigingsbestanden voor het
hoger onderwijs inleest en omzet naar schone, onderzoeksklare data (Parquet en
een star schema), met een Streamlit-app erbovenop. Het project is de
HO-tegenhanger van `cedanl/mbo-bekostiging-bestanden` en **lijkt daar zo veel
mogelijk op**: dezelfde mappen, tooling, modulenamen, fasen, CLI-vorm,
app-opbouw en coding principles.

Doelgroep: analisten en onderzoekers bij hogescholen en universiteiten die met
bekostigingsdata werken. De tool draait binnen één instelling en rekent de
bekostiging **niet** opnieuw uit; hij maakt de inhoud van de DUO-bestanden
toegankelijk.

**Succes voor v1:**
- Een analysebestand (VLPBEK, DEFBEK en/of HISBEK) in `data/01-raw/` zetten en
  op **Verwerk alles** klikken levert een star schema en een werkend dashboard op.
- Het werkt met elke combinatie van leveringen, ook **zonder HISBEK** en met
  maar één VLPBEK.
- Alles draait direct op synthetische demo-data in de repo.
- `uv run pytest`, `ruff` en `ty` zijn groen in CI.

## 2. Labels in dit document

Omdat de inhoudelijke HO-kennis (nog) niet door de opdrachtgever te controleren
is, staan onzekere punten gemarkeerd:

- **[Bevestigd]** — gelezen uit de HO-PvE (v26.3.1, 17-07-2026) of het
  voorbeeldbestand in `cedanl/wisselstroom`.
- **[Te checken]** — aanname; laten bevestigen door een collega met
  HO-bekostigingskennis of door DUO.

## 3. Scope

**In v1:** het *analysebestand* in drie soorten levering.

| Levering | Betekenis | Recordsoorten | Bron |
|---|---|---|---|
| `VLPBEK` | Voorlopige bekostiging | VLP, BLB, BRD, BRR, SLR | PvE bijlage 8 (§17) **[Bevestigd]** |
| `DEFBEK` | Definitieve bekostiging | idem | PvE bijlage 8 (§17) **[Bevestigd]** |
| `HISBEK` | Historische bekostiging (alle definitieve jaren) | VLP, HRD, HRR, SLR | PvE bijlage 10 (§19) **[Bevestigd]** |

Elke soort levering is **optioneel**. Niet elke instelling heeft een
HISBEK-bestand **[Te checken: hoe vaak instellingen HISBEK aanvragen]**.

**Buiten v1 (YAGNI, als vervolg in de README):** OBO, verschillenlijst OBOV,
landelijk overzicht, registratieoverzicht, wisselstroom-labels, rendement en
cohorten uit HISBEK, en een gedeelde MBO/HO-kernbibliotheek (zie §11).

## 4. Bestandsformaat (samenvatting PvE)

- Tekst, UTF-8, velden gescheiden door `|`, geen kopregel. Het eerste veld is
  de recordsoort. **[Bevestigd]**
- Bestandsnaam: `TTTTTT_JJJJ_EEJJMMDD_99XX.CSV`, met TTTTTT de soort levering,
  JJJJ het bekostigingsjaar (bij HISBEK: het laatste bekostigingsjaar),
  EEJJMMDD de aanmaakdatum en 99XX de BRIN van de ontvanger. **[Bevestigd]**
- Datums als `jjjjmmdd`; booleans als `J`/`N`. **[Bevestigd]**
- Alle regels in het bestand zijn opgevuld tot hetzelfde aantal velden (25 in
  het voorbeeld), dus lege velden aan het eind zijn normaal. **[Bevestigd]**
- BLB bestaat in een oude versie (tot september 2019, bestandsnaam `_OUD`) en
  in de huidige versie met graaddatums AD/ADLG en verbruikstellers.
  **[Bevestigd]** v1 ondersteunt alleen de **huidige** versie. Door het
  opvullen is de versie niet aan het aantal velden te herkennen.
  **[Te checken: of oude bestanden nog gebruikt worden]**
- Een aantal van `-1` in BLB betekent "n.v.t." (eerdere graad). **[Bevestigd]**
- `CodeBekostigingstatus` bevat één of meer codes van twee kleine letters,
  oplopend en gescheiden door komma's, bijvoorbeeld `na,ti`. **[Bevestigd]**
- Het bestand bevat ook deelnames en resultaten bij **andere instellingen**
  van dezelfde student (bijvoorbeeld `71AA` naast `99XX`). **[Bevestigd]**
- Datums waarvan de dag of maand `00` is komen in de PvE voor bij
  periodegegevens van personen (OBO). Of dat ook in het analysebestand
  voorkomt is **[Te checken]**. De decoder vangt het in ieder geval af.

Exacte veldnamen, volgorde en typen per recordsoort staan in de TOML-schema's
(§5) en zijn overgenomen uit PvE §17.7 en §19.7.

## 5. Architectuur

```
data/01-raw/  ──ingest──►  decode ──► validate ──► export ──► data/02-prepared/<levering>/
                                                               │
                                                  stack ◄──────┘
                                                    │
                                                  star ──► data/03-output/star/ ──► app
```

Repo: `ho-bekostiging-bestanden`, package `ho_bekostiging_bestanden`,
CLI-commando `ho`.

| Module | Taak |
|---|---|
| `metadata/analyse_schema.toml` | Veldindeling VLP/BLB (oud en nieuw)/BRD/BRR/SLR, met `date_fields`, `bool_fields` en `int_fields` (zelfde vorm als `ro_schema.toml` bij MBO) |
| `metadata/hisbek_schema.toml` | Veldindeling VLP/HRD/HRR/SLR |
| `metadata/bekostigingstatus.csv` | 34 codes: `Code`, `Omschrijving`, `Groep`, `Bekostigd` (J/N). De omschrijvingen komen uit de PvE (§19.7.5) **[Bevestigd]**. De groepsindeling komt uit rapport-bijlage B en is een eigen indeling, **niet van DUO** **[Te checken]** |
| `metadata/*.csv` (overige codelijsten) | Opleidingsniveau, opleidingsfase, onderwijsvorm, inschrijvingsvorm, bekostigingsniveau, opleidingsonderdeel, bekostigingscode, IndicatieBaMa (waardelijsten uit de PvE) |
| `metadata/__init__.py` | `load_schema(naam)`, `load_codelijst(naam)` |
| `ingest.py` | Generieke multi-record-reader die splitst per recordsoort en regels afknipt of aanvult tot het schema. `parse_bestandsnaam()` geeft levering, jaar, aanmaakdatum en BRIN. |
| `decode.py` | Typen omzetten: datums (ongeldig wordt `null` en de ruwe waarde blijft in `<Veld>_Ruw`), J/N naar boolean, getallen, `-1` naar `null` met een vlag `<Veld>_NVT`, `CodeBekostigingstatus` blijft tekst (bijvoorbeeld `na,ti`), zodat CSV-export werkt; de brugtabel in het star schema splitst de codes |
| `validate.py` | Controles die niets tegenhouden en een rapport opleveren: tellingen in SLR tegen het werkelijke aantal, verplichte velden, codes die niet in een codelijst staan, onbekende recordsoorten, BRIN in bestandsnaam tegen VLP |
| `export.py` | Parquet (standaard) of CSV |
| `pipeline.py` | `detect_levering()`, `run_pipeline(source, target)`, `run_star()`. Een onbekende bestandsnaam geeft een `ValueError`. Schrijft naast de recordsoorten twee extra tabellen: `LEVERING` (één rij met de gegevens uit bestandsnaam en VLP) en `VALIDATIE` (de meldingen) |
| `stack.py` | Prepared-mappen stapelen met de kolommen `Levering`, `Bekostigingsjaar`, `DatumAanmaak`, `Bestandsnaam` |
| `star.py` | Star schema bouwen (§6) |
| `indicatoren.py` | Pure functies op het star schema voor het dashboard (trechter, redenen, per opleiding, voorlopig tegenover definitief, historie), net als `indicatoren.py` bij MBO |
| `cli.py` | `ho verwerk <bestand> <doel>`, `ho star <mappen…> --doel <map>` |

Paden en drempelwaarden staan in `app/config.toml` en in constanten bovenaan
de modules; er staan geen vaste waarden midden in de code.

## 6. Star schema

Negen Parquet-bestanden in `data/03-output/<bron>/star/datamodel/`. Net als bij
MBO worden **natuurlijke sleutels** gebruikt: `levering` (label van de
prepared-map, gelijk aan de bestandsstam), `_persoon_id` (BSN, anders
onderwijsnummer), `BRIN`, `Opleidingscode` en `Code`. Feitrijen krijgen een
`_feit_id` (`D:`/`R:` + levering + rijnummer), zodat de brugtabel ernaar kan
verwijzen; dat is nodig omdat `Inschrijvingvolgnummer` in HRD niet verplicht is.

**Dimensies**

| Tabel | Sleutel | Inhoud | Bron |
|---|---|---|---|
| `dim_levering` | `levering` | SoortLevering (VLPBEK/DEFBEK/HISBEK), Bekostigingsjaar, DatumAanmaak, BrinOntvanger, Bestandsnaam | tabel `LEVERING` |
| `dim_persoon` | `_persoon_id` | Burgerservicenummer, Onderwijsnummer, datums behaalde graden (AD/ADLG/Ba/BaLG/Ma/MaLG). De velden worden over leveringen heen samengevoegd (nieuwste levering eerst), zoals MBO #41 | BLB, BRD, BRR, HRD, HRR |
| `dim_instelling` | `BRIN` | `EigenInstelling` (BRIN komt voor als BrinOntvanger) | BRD/BRR/HRD/HRR |
| `dim_opleiding` | `Opleidingscode` | Opleidingsniveau, OpleidingOnderdeel, IndicatieSectorLG, IndicatieAcademischZiekenhuis (nieuwste levering eerst) | BRD/BRR/HRD/HRR |
| `dim_status` | `Code` | Omschrijving, Groep, Bekostigd | `bekostigingstatus.csv` |

**Feiten**

| Tabel | Één rij per | Belangrijke kolommen |
|---|---|---|
| `fact_deelname` | deelname × levering (BRD + HRD) | sleutels, Inschrijvingvolgnummer, Bekostigingsindicatie, Opleidingsfase, Onderwijsvorm, Inschrijvingsvorm, DatumInschrijving, DatumUitschrijving, EersteInschrijving, Bekostigingsniveau, Bekostigingsduur, Bekostigingscode, IndicatieBaMa, IndicatieNationaliteitsvoorwaardeSF, IndicatieGBARelatie, Bekostigingsjaar |
| `fact_resultaat` | graad × levering (BRR + HRR) | sleutels, Resultaatvolgnummer, Bekostigingsindicatie, Opleidingsfase, datum graad, ECTS, ECTSBekostigd, JointDegreeFactor, Bekostigingsjaar |
| `fact_status` | (deelname of resultaat) × statuscode | brugtabel: `_feit_id`, `Bron` (deelname/resultaat), `levering`, `Code` |
| `fact_loopbaan` | persoon × levering (BLB) | verbruikstellers en aantallen bekostigde inschrijvingen (`-1` wordt `null` met een NVT-vlag) |

Bij HRD en HRR komt het bekostigingsjaar uit het record zelf; bij BRD en BRR
uit de VLP. **[Bevestigd]** Velden die in HRD/HRR ontbreken blijven `null`.

**Invarianten** (getest): elke sleutel is uniek in zijn dimensie; elke
verwijzing in een feittabel bestaat in de dimensie; het aantal rijen in
`fact_deelname` is gelijk aan het aantal BRD- plus HRD-records na het stapelen.

## 7. App (Streamlit)

Zelfde opbouw als bij MBO: `app/main.py` (navigatie, geen bedrijfslogica),
`app/pages/home.py`, `dashboard.py`, `resultaten.py`, `app/_chart_docs.py`,
`app/_tabel_docs.py`, `app/_utils.py` en `app/config.toml`.

- **Home:** toont de gevonden bestanden (levering, jaar, BRIN) en biedt
  uploaden van een los bestand en **Verwerk alles**. Het validatierapport
  staat per bestand als waarschuwing.
- **Dashboard** (filters: bekostigingsjaar, levering, opleidingsniveau):
  1. Bekostigingstrechter: deelnames en graden bij de eigen instelling:
     "in bestand" → "beoordeeld" (zonder status `mv`, want die deelnames
     vallen buiten de beoordeling) → "bekostigd". **[Te checken: of `mv`
     de juiste afbakening is voor "beoordeeld"]**
  2. Waarom niet bekostigd: aantallen per statusgroep en per code, met de
     omschrijving in gewone taal.
  3. Per opleiding: aandeel bekostigd.
  4. Voorlopig tegenover definitief: welke statussen zijn veranderd. Alleen
     zichtbaar als VLPBEK en DEFBEK voor hetzelfde jaar er allebei zijn.
  5. Historie per bekostigingsjaar: alleen zichtbaar met HISBEK; anders een
     korte uitleg.
- **Resultaten:** een star-tabel kiezen, een voorbeeld van 1.000 rijen zien en
  als CSV downloaden.

Elke grafiek heeft een toelichting in `_chart_docs.py` en elke tabel een
beschrijving in `_tabel_docs.py`. Een grafiek zonder toelichting is niet af.

## 8. Demo-data

Het voorbeeldbestand in `cedanl/wisselstroom` heeft de juiste structuur, maar
de inhoud is gemaskeerd met `x`. Daarom komt er
`scripts/genereer_demo.py` (vaste seed, reproduceerbaar), dat schrijft naar
`data/01-raw/demo/`:

- `VLPBEK_2025_…_99XX.csv` en `DEFBEK_2025_…_99XX.csv` (zelfde jaar, deels
  andere statussen);
- `VLPBEK_2026_…_99XX.csv`;
- `HISBEK_2024_…_99XX.csv`.

Kenmerken: fictieve BRIN `99XX` plus een andere instelling `71AA`; fictieve
BSN's en onderwijsnummers in de reeks `7000xxxxx`/`8000xxxxx`, zoals in het
wisselstroom-voorbeeld; een realistische mix van niveaus, fasen,
onderwijsvormen en statuscodes (ook meervoudige zoals `na,ti`); de huidige
BLB-versie. Er komen geen echte persoonsgegevens in git;
echte data staat in `.gitignore`.

## 9. Foutafhandeling

| Situatie | Gedrag |
|---|---|
| Onbekende bestandsnaam | `ValueError` met duidelijke tekst; de app toont een melding en slaat het bestand over |
| Onbekende recordsoort | overslaan en melden in het validatierapport |
| Te veel of te weinig velden in een regel | afknippen of aanvullen tot het schema (zoals bij MBO), melden in het rapport |
| Ongeldige datum | `null`, ruwe waarde in `<Veld>_Ruw` |
| SLR-telling klopt niet | waarschuwing, verwerking gaat door |
| Leeg bestand of bestand zonder VLP | `ValueError` |

## 10. Tests

pytest op de demo-data. Tijdens het bouwen worden tests eerst geschreven (TDD).

- `test_ingest.py`: splitsen per recordsoort, bestandsnaam ontleden, opgevulde regels, onbekende recordsoorten
- `test_decode.py`: datums, J/N, `-1` naar n.v.t., getallen
- `test_validate.py`: SLR-tellingen, onbekende codes of recordsoorten
- `test_metadata.py`: 34 statuscodes aanwezig, geen dubbele codes, elke code heeft een groep
- `test_stack.py`, `test_star.py`: invarianten uit §6
- `test_pipeline.py`: alle leveringen · **zonder HISBEK** · alleen één VLPBEK · alleen HISBEK
- `test_cli.py`

CI (GitHub Actions): `ruff check`, `ruff format --check`, `ty check`, `pytest`.

## 11. Vervolg (niet in v1)

1. Overige HO-bestanden: OBO, OBOV, registratieoverzicht, landelijk overzicht.
2. Wisselstroom-labels en rendement of cohorten uit HISBEK (overlap met `cedanl/wisselstroom`).
3. Gedeelde MBO/HO-kernbibliotheek, als na v1 duidelijk is welke code echt gedeeld is.
4. Namen van opleidingen en instellingen via RIO (`cedanl/rio-onderwijsdata`).
5. Ondersteuning voor de oude BLB-versie (`_OUD`, tot 2019), als daar vraag naar is.
6. Laten bevestigen: alle **[Te checken]**-punten in dit document.

## 12. Repo en werkwijze

- Lokaal in `C:\Users\Aslam\Projects\ho-bekostiging-bestanden`. De GitHub-repo
  onder `cedanl` wordt pas aangemaakt na expliciete opdracht.
- Er wordt pas gecommit na expliciete opdracht (coding principle). Deze spec
  is gecommit met toestemming.
- Werkwijze: superpowers-flow (spec → plan → TDD → uitvoering per taak → review).
