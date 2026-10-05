# Recordtypes

Alle bestanden zijn opgebouwd uit records zonder kolomkoppen, gescheiden door `|`. Het eerste
veld van elke regel is altijd de **recordsoort**.

## Overzicht

| Code | Naam | VLPBEK / DEFBEK | HISBEK | Beschrijving |
|---|---|:---:|:---:|---|
| [`VLP`](vlp.md) | Voorlooprecord | ✓ | ✓ | Eerste record; instelling, jaar en aanmaakdatum |
| [`BLB`](blb.md) | Bekostigingsloopbaan student | ✓ | | Behaalde graden en verbruikte inschrijfjaren per student |
| [`BRD`](brd.md) | Bekostigingsresultaat deelname | ✓ | | Een inschrijving met haar bekostigingsstatus |
| [`BRR`](brr.md) | Bekostigingsresultaat resultaat | ✓ | | Een graad met haar bekostigingsstatus |
| [`HRD`](hrd.md) | Historisch resultaat deelname | | ✓ | Historische variant van BRD, met eigen jaar |
| [`HRR`](hrr.md) | Historisch resultaat resultaat | | ✓ | Historische variant van BRR, met eigen jaar |
| [`SLR`](slr.md) | Sluitrecord | ✓ | ✓ | Laatste record; aantal records per soort |

## Veldnotatie

In de tabellen per recordtype staat bij elk veld:

| Kolom | Betekenis |
|---|---|
| Pos | Positie in de regel; de positie bepaalt de betekenis |
| Veld | Veldnaam uit het PvE |
| Verplicht | `Ja` als de tool het veld als verplicht controleert (zie het schema); een leeg verplicht veld is een *error* |
| Type | Het type na het decoderen |
| Definitie | Betekenis, met een verwijzing naar de [waardenlijst](../waardenlijsten.md) als er een is |

De typen na het decoderen:

| Type | Ruwe notatie | Na het decoderen |
|---|---|---|
| Datum | `jjjjmmdd` | `Date`; een ongeldige datum wordt `null`, de ruwe waarde blijft in `<veld>_Ruw` |
| `J`/`N` | `J` of `N` | `Boolean`; iets anders wordt `null` |
| Geheel getal | cijfers | `Int64` |
| Decimaal getal | cijfers met komma of punt | `Float64` |
| Tekst | alles anders | tekst; een leeg veld wordt `null` |

## Veldvolgorde

In de bestanden bepaalt de **positie** de betekenis. De veldvolgorde staat in
`src/ho_bekostiging_bestanden/metadata/analyse_schema.toml` (VLPBEK/DEFBEK) en
`hisbek_schema.toml` (HISBEK), afgeleid uit het PvE. Een regel die korter is dan het schema
wordt aangevuld met lege velden; een regel met extra gevulde velden geeft een melding.

## Gedeelde velden

Deze velden komen in meerdere recordsoorten voor en hebben overal dezelfde betekenis:

| Veld | Betekenis |
|---|---|
| `Recordsoort` | Altijd het eerste veld |
| `Burgerservicenummer` | BSN, 9 tekens; leeg als alleen een onderwijsnummer is gevuld |
| `Onderwijsnummer` | Alternatief voor het BSN, 9 tekens |
| `BRIN` | 2 cijfers + 2 hoofdletters; de instelling |
| `Inschrijvingvolgnummer` | Volgnummer van een inschrijving, uniek per BRIN |
| `Resultaatvolgnummer` | Volgnummer van een resultaat, uniek per BRIN |
| `Opleidingscode` | ISAT-code van de opleiding, 5 tekens |
| `CodeBekostigingstatus` | Eén of meer statuscodes, bijvoorbeeld `na,ti` |
| `Bekostigingsindicatie` | `J`/`N`: wel of niet bekostigd |
