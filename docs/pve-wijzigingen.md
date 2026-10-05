# PvE-versies

De veldindelingen en codelijsten komen uit het DUO **Programma van Eisen (PvE) HO-instelling**:

| Onderdeel | PvE |
|---|---|
| Analysebestand VLPBEK/DEFBEK (VLP, BLB, BRD, BRR, SLR) | bijlage 8, §17 |
| Historisch bestand HISBEK (VLP, HRD, HRR, SLR) | bijlage 10, §19 |
| Bekostigingsstatussen | §19.7.5 |

De huidige versie is **26.3.1 (17-07-2026)**. Het schema legt dat vast als
`schema_version = "26.3.1"` in `analyse_schema.toml` en `hisbek_schema.toml`, en de brondata
bewaart het per levering in de tabel `LEVERING` (`SchemaVersie`).

De PvE-PDF staat niet in deze repo (alle `*.pdf` zijn genegeerd in git). De volledige PDF
staat in `cedanl/mbo-bekostiging-bestanden`.

## Een nieuwe versie verwerken

1. Lees de wijzigingen in het versiebeheer van het PvE en kijk welke raken aan bijlage 8 of
   10.
2. Vergelijk de recordbeschrijvingen met de schema's. De veldvolgorde van HRD en HRR staat
   uitgeschreven in `tests/test_pve_hisbek.py`, los van het schema.
3. Werk per inhoudelijk verschil het schema (`metadata/*_schema.toml`) of de codelijst
   (`metadata/*.csv`) bij, of leg hieronder vast waarom er geen gevolg is.
4. Werk `schema_version` bij, draai `uv run pytest`, en werk de
   [Recordtypes](recordtypes/index.md) bij. Een test controleert dat elk schema-veld in de
   bijbehorende pagina staat, in dezelfde volgorde.
5. Voeg hieronder een kopje met de wijzigingen toe.

## 26.3.1 (17-07-2026)

De eerste versie waarmee deze repo is opgebouwd.

### Controle van het schema tegen het PvE

Het analysebestand-, HISBEK-schema en de codelijsten zijn veld voor veld vergeleken met
bijlage 8 en 10. De veldvolgorde van VLP, HRD, HRR en SLR klopte. Drie punten zijn
aangepast (zie `docs/superpowers/specs/2026-10-05-hisbek-pve-conformiteit-design.md`):

| Punt | Wijziging |
|---|---|
| Inschrijvingsvorm in HRD kent `A`, `E`, `S` en `T` (§19.7.2); in BRD alleen `E` en `S` | Eigen codelijst `inschrijvingsvorm_hisbek.csv` |
| Verplichte velden in HRD (`DatumUitschrijving`, `IndicatieNationaliteitsvoorwaardeSF`) en HRR (`Onderwijsvorm`) werden niet gecontroleerd | `required_fields` gelijkgetrokken met "Verplicht = ja" |
| De demo-data was onrealistisch (ECTS bij een niet-OU-instelling, woonplaats- en deelstaatvelden na 2014, geen aflopende sortering) | Demo-generator aangepast |

### Bekende verschillen met het PvE

Deze afwijkingen zijn bewust soepeler dan het PvE:

| Veld | PvE | Schema | Gevolg |
|---|---|---|---|
| `Opleidingsfase` in BRR | geen `S` (schakelprogramma) | één lijst voor BRD en BRR, mét `S` | Een `S` in BRR geeft geen codelijstmelding |
| `IndicatieBaMa` in BRD | `B`, `M`, `D` | één lijst voor BRD en BRR, mét `A` (*master met impliciete bachelor*, alleen in BRR) | Een `A` in BRD geeft geen codelijstmelding |

### BLB-versies

Het PvE beschrijft twee versies van het BLB-record: de **oude** versie (tot september 2019,
zonder `DatumGraadBehaaldAD`/`ADLG` en zonder de `Verbruik…`-velden) en de **nieuwe** versie.
Het PvE noemt de oude versie ook "huidige versie ('naam-OUD')", wat verwarrend is. Het
schema volgt de **nieuwe** versie.

Een bestand met `_OUD` in de naam wordt niet herkend en overgeslagen. Of er nog bestanden
met de oude BLB worden gebruikt, is **[Te checken]**.

### Nog te bevestigen

Zie de [Ontwerpkeuzes](ontwerpkeuzes.md) voor de aannames, onder andere:

- de groepsindeling van de statuscodes (eigen indeling, niet van DUO);
- `mv` als afbakening van *beoordeeld* in de trechter;
- of de oude BLB-versie nog voorkomt;
- een echt HISBEK-bestand om te bevestigen dat DUO het PvE volgt.
