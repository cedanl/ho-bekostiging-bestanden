# Release-blokkers v0.1.0 — design

## Aanleiding
De audit van 2026-10-05 vond twee punten die een eerste release blokkeren:

1. **`ho verwerk` wist eigen bestanden in de doelmap.** `pipeline._maak_leeg`
   verwijdert elke `*.parquet` en `*.csv` in `target`, zodat een recordsoort
   die in een nieuwe versie van het bestand ontbreekt niet blijft hangen. Wie
   per ongeluk een map met eigen bestanden opgeeft, is die kwijt.
2. **De app pseudonimiseert echte data met de openbare demo-sleutel.** Zonder
   `EENCIJFERHO_ENCRYPT_KEY` valt de app terug op `demo_sleutel` uit
   `app/config.toml`, ook voor geüploade of eigen bestanden. Met een openbare
   sleutel is een pseudoniem terug te rekenen naar het BSN (de BSN-ruimte is
   klein). Er is alleen een waarschuwing.

## Ontwerp

### 1. Alleen eigen tabellen opruimen
`_maak_leeg` verwijdert alleen `<tabel>.<fmt>` voor de tabellen die de
pipeline kan schrijven: de recordsoorten uit alle schema's
(`SCHEMA_PER_LEVERING`) plus `LEVERING` en `VALIDATIE`. De namen komen uit de
schema-TOML's, niet uit een vaste lijst. Andere bestanden blijven staan.

Alternatieven die afvielen:
- *Weigeren bij een niet-lege map*: breekt opnieuw verwerken naar dezelfde map.
- *Markerbestand*: extra toestand op schijf voor hetzelfde resultaat.

Restrisico: een eigen bestand dat toevallig `BRD.parquet` heet. Aanvaardbaar.

### 2. Demo-sleutel alleen voor demo-data (fail-closed)
Een bestand is demo-data als de BRIN in de bestandsnaam **en** in het
VLP-record gelijk is aan de demo-BRIN (`demo.BRIN_EIGEN`, `99XX`). Het
VLP-record wordt ook gelezen, zodat een omgedoopt echt bestand niet
doorglipt; alleen de eerste regel wordt gelezen.

`_utils.pseudonimiseringssleutel(bestanden)` geeft bij de demo-sleutel een
fout zodra één bestand geen demo-data is, met de namen van die bestanden. De
Home-pagina toont die fout al en zet de knop *Verwerk alles* uit. De
omgevingsvariabele gaat zoals nu altijd voor; zonder pseudonimisering is geen
sleutel nodig en geldt de check niet.

De herkenning staat in `demo.py` (bedrijfslogica, testbaar zonder Streamlit);
de app roept hem alleen aan.

## Tests
- Een eigen bestand in de doelmap blijft staan na `run_pipeline`.
- Een recordsoort uit een eerdere verwerking wordt wel opgeruimd (bestond nog
  niet als test).
- `is_demo_bestand`: demo-bestand → waar; andere BRIN in de naam → onwaar;
  demo-naam met een andere BRIN in de VLP → onwaar.
- App: met de demo-sleutel en een niet-demo-bestand in de invoermap is de
  knop uit en staat het bestand in de foutmelding; met de env-var gezet
  verwerkt de app gewoon.

## Documentatie
`docs/aan-de-slag.md` (sleutelkader) en `docs/ontwerpkeuzes.md` (twee
keuzes) worden bijgewerkt.
