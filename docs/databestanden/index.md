# Databestanden

DUO levert aan HO-instellingen drie soorten analysebestanden. Ze hebben dezelfde structuur
(multi-record, `|`-gescheiden, UTF-8, geen kopregel) maar een eigen doel en tijdsmoment.

---

## Overzicht

| Bestand | Code | Recordsoorten | Bestandsnaam | Bron in het PvE |
|---|---|---|---|---|
| Voorlopige bekostiging | VLPBEK | VLP, BLB, BRD, BRR, SLR | `VLPBEK_JJJJ_EEJJMMDD_99XX.CSV` | bijlage 8 (§17) |
| Definitieve bekostiging | DEFBEK | VLP, BLB, BRD, BRR, SLR | `DEFBEK_JJJJ_EEJJMMDD_99XX.CSV` | bijlage 8 (§17) |
| Historische bekostiging | HISBEK | VLP, HRD, HRR, SLR | `HISBEK_JJJJ_EEJJMMDD_99XX.CSV` | bijlage 10 (§19) |

---

## Wat zit er in elk bestand?

### VLPBEK en DEFBEK — het analysebestand

Een analysebestand voor **één instelling** en **één bekostigingsjaar**. Het bevat van alle
inschrijvingen (*deelnames*) en graden (*resultaten*) die van belang zijn voor dat jaar het
resultaat van de bepaling van de bekostigingsstatus, met de grondslag erbij. Het bestand
laat dus zien **wat** bekostigd wordt en, zo niet, **waarom niet**.

Het verschil: `VLPBEK` is de **voorlopige** bepaling, `DEFBEK` de **definitieve**. Door ze
naast elkaar te leggen zie je welke statussen tussen voorlopig en definitief veranderden (zie
[Dashboard](../dashboard.md)).

→ [Volledige beschrijving](analysebestand.md)

### HISBEK — historische bekostiging

Eén bestand met de bekostiging van **alle definitieve jaren in het verleden**, met een eigen
bekostigingsjaar per record. Handig voor een tijdreeks. Niet elke instelling heeft zo'n
bestand; het is optioneel.

→ [Volledige beschrijving](hisbek.md)

---

## Gedeelde recordstructuur

- Elke regel begint met de **recordsoort** (`VLP`, `BLB`, …). De positie van de velden
  bepaalt hun betekenis; er zijn geen kolomkoppen.
- Alle regels zijn opgevuld tot hetzelfde aantal velden. Lege velden aan het eind zijn dus
  normaal.
- Datums zijn `jjjjmmdd`, booleans `J`/`N`, en decimalen kunnen een komma of punt hebben.
- Het bestand mag geen lege regels of onverwachte tekens (zoals tabs) bevatten.
- De bestanden bevatten ook deelnames en resultaten van dezelfde student bij **andere
  instellingen** (bijvoorbeeld `71AA` naast de eigen `99XX`). De tool markeert de eigen
  instelling met `EigenInstelling` in `dim_instelling`.

Zie [Recordtypes](../recordtypes/index.md) voor de velden per recordsoort.
