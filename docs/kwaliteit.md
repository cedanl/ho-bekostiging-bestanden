# Kwaliteit

Elke levering en het star schema worden gecontroleerd. De uitkomst is een **status** met
**meldingen**, zodat je kunt zien of je de cijfers kunt vertrouwen en waar het misgaat. De
uitvoer wordt altijd geschreven, ook bij een fout, zodat je de oorzaak kunt nalezen.

## Meldingen en status

Elke melding heeft een **ernst**:

| Ernst | Betekenis |
|---|---|
| `error` | Er is iets mis dat de cijfers kan beïnvloeden. Eén error zet de status op `fail`. |
| `warning` | Opvallend, maar de cijfers blijven bruikbaar. De status wordt `warn`. |

| Status | Betekenis |
|---|---|
| `ok` | Geen meldingen |
| `warn` | Alleen warnings |
| `fail` | Minstens één error |

## Controles

### Per levering

Deze controles draaien bij het verwerken van een bestand. De meldingen staan in de tabel
`VALIDATIE` van de brondata.

| Controle | Ernst | Wat wordt gecontroleerd |
|---|---|---|
| Inlezen | error | Een onbekende recordsoort, of gevulde velden voorbij het schema |
| Aantal records | error | De tellingen in het [SLR](recordtypes/slr.md) komen overeen met het aantal ingelezen records; ontbreekt het SLR, dan ook een error |
| Eén rij | error | VLP en SLR hebben precies één rij |
| Verplicht veld | error | Een verplicht veld is leeg (zie *Verplicht* in de [Recordtypes](recordtypes/index.md)) |
| BRIN | error | De BRIN in de bestandsnaam wijkt af van die in het VLP (verkeerde instelling) |
| Bekostigingsjaar | warning | Het jaar in de bestandsnaam wijkt af van dat in het VLP; het VLP is leidend |
| Codelijst | warning | Een code staat niet in de [waardenlijst](waardenlijsten.md). Onbekende statuscodes komen in `dim_status` als *Onbekende code* |

Een bestand zonder voorlooprecord wordt helemaal niet verwerkt.

### Per bestand in een map

Bij **Verwerk alles** (`verwerk_alles`) komen daar twee controles bij:

| Controle | Ernst | Wat wordt gecontroleerd |
|---|---|---|
| Bestand | error | Het bestand kon niet verwerkt worden (bijvoorbeeld zonder VLP), dus het ontbreekt in de cijfers |
| Dubbel | warning | Een bestand met dezelfde naam is al verwerkt; het tweede is overgeslagen |

### Op het star schema

Deze controles draaien bij het bouwen van het [datamodel](datamodel.md#relaties-en-controles).

| Controle | Ernst | Wat wordt gecontroleerd |
|---|---|---|
| Uniciteit | error | Een sleutel komt meer dan eens voor in zijn tabel |
| Lege sleutel | error | Een sleutelkolom bevat `null` |
| Koppeling | error | Een waarde in een feittabel bestaat niet in de dimensie waar hij naar verwijst |

Daarnaast weigert het bouwen van het star schema een mix van gepseudonimiseerde en
niet-gepseudonimiseerde leveringen (een `ValueError`), omdat studenten dan stil dubbel
geteld zouden worden.

## quality.json

`ho star` en **Verwerk alles** schrijven `quality.json` naast het star schema. Het
JSON-schema staat in `src/ho_bekostiging_bestanden/metadata/quality.schema.json`.

| Veld | Inhoud |
|---|---|
| `status` | `ok`, `warn` of `fail` voor het geheel |
| `fouten_toegestaan` | Of de aanroeper een `fail` heeft toegestaan (`--allow-quality-errors`) |
| `total_errors`, `total_warnings` | Aantal meldingen per ernst |
| `provenance` | Pakketversie, Python- en Polars-versie en het tijdstip van aanmaken |
| `leveringen` | Per levering: bestandsnaam, **sha256** van het bronbestand, status en meldingen |
| `star` | Status en meldingen van het star schema |
| `dekking` | Het aantal rijen per levering × recordsoort; een recordsoort zonder rijen telt als 0, zodat een ontbrekend deel van een levering opvalt |

De sha256 laat zien welk bestand precies is verwerkt. Een melding bevat `controle`,
`recordsoort`, `melding`, `aantal` en `ernst`.

## Exitcodes

| Exitcode | Betekenis |
|---|---|
| 0 | Klaar; status `ok` of `warn` |
| 1 | Invoerfout (onbekend bestand, geen VLP, geen sleutel) |
| 3 | Kwaliteitsstatus `fail` |

Met `--allow-quality-errors` (bij `ho verwerk` en `ho star`) geeft een `fail` exitcode 0
en een regel *Let op: kwaliteitsstatus fail*. In Python werpen `run_pipeline` en `run_star`
een `KwaliteitsFout` bij `fail`; met `fail_on_errors=False` niet.

## In de app

De app toont de status op Home en als banner op het Dashboard en de Resultaten. Per bestand
zie je de meldingen van de controles. Een bestand dat niet herkend of niet verwerkt kon
worden, staat erbij met de reden, zodat het niet stil uit de cijfers verdwijnt.
