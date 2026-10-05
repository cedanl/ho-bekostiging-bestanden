# BLB – Bekostigingsloopbaan student

Per student nul of één BLB-record, met de **bekostigingsloopbaan**: wanneer de eerste
graad per type is behaald en hoeveel bekostigde inschrijfjaren de student al heeft
verbruikt. DUO gebruikt dit om te bepalen of een nieuwe inschrijving nog bekostigd
kan worden. Alleen in het analysebestand (VLPBEK en DEFBEK).

| Pos | Veld | Verplicht | Type | Definitie |
|---|---|---|---|---|
| 1 | `Recordsoort` | Ja | Tekst | Aanduiding van het record; altijd de recordcode van deze pagina. |
| 2 | `Burgerservicenummer` | Nee | Tekst | BSN van de student, 9 tekens (indien nodig met voorloopnul). Leeg als de student alleen een onderwijsnummer heeft. |
| 3 | `Onderwijsnummer` | Nee | Tekst | Nummer voor een student zonder (verifieerbaar) BSN, 9 tekens (indien nodig met voorloopnul). |
| 4 | `DatumGraadBehaaldAD` | Nee | Datum (`jjjjmmdd`) | Datum waarop de vroegste (eerste) graad van dit type is behaald. Associate Degree. |
| 5 | `DatumGraadBehaaldADLG` | Nee | Datum (`jjjjmmdd`) | Datum waarop de vroegste (eerste) graad van dit type is behaald. Associate Degree in de LG-sector. |
| 6 | `DatumGraadBehaaldBa` | Nee | Datum (`jjjjmmdd`) | Datum waarop de vroegste (eerste) graad van dit type is behaald. Bachelor. |
| 7 | `DatumGraadBehaaldBaLG` | Nee | Datum (`jjjjmmdd`) | Datum waarop de vroegste (eerste) graad van dit type is behaald. Bachelor in de LG-sector. |
| 8 | `DatumGraadBehaaldMa` | Nee | Datum (`jjjjmmdd`) | Datum waarop de vroegste (eerste) graad van dit type is behaald. Master. |
| 9 | `DatumGraadBehaaldMaLG` | Nee | Datum (`jjjjmmdd`) | Datum waarop de vroegste (eerste) graad van dit type is behaald. Master in de LG-sector. |
| 10 | `VerbruikAD` | Nee | Geheel getal | Aantal bekostigde inschrijfjaren dat meetelt voor de vraag of een inschrijving voor Associate Degree (niet LG) bekostigd wordt. `-1` = n.v.t. `-1` wordt `null` met vlag `VerbruikAD_NVT`. |
| 11 | `VerbruikADLG` | Nee | Geheel getal | Idem, voor Associate Degree in de LG-sector. `-1` = n.v.t. `-1` wordt `null` met vlag `VerbruikADLG_NVT`. |
| 12 | `VerbruikBA` | Nee | Geheel getal | Idem, voor Bachelor (niet LG). `-1` = n.v.t. `-1` wordt `null` met vlag `VerbruikBA_NVT`. |
| 13 | `VerbruikBALG` | Nee | Geheel getal | Idem, voor Bachelor in de LG-sector. `-1` = n.v.t. `-1` wordt `null` met vlag `VerbruikBALG_NVT`. |
| 14 | `VerbruikMA` | Nee | Geheel getal | Idem, voor Master (niet LG). `-1` = n.v.t. `-1` wordt `null` met vlag `VerbruikMA_NVT`. |
| 15 | `VerbruikMALG` | Nee | Geheel getal | Idem, voor Master in de LG-sector. `-1` = n.v.t. `-1` wordt `null` met vlag `VerbruikMALG_NVT`. |
| 16 | `AantalBekostigdeInschrijvingenBa` | Nee | Geheel getal | Aantal bekostigde inschrijfjaren van de student aan een Bachelor of gelijkgestelde opleiding. `-1` wordt `null` met vlag `AantalBekostigdeInschrijvingenBa_NVT`. |
| 17 | `AantalBekostigdeInschrijvingenBaLG` | Nee | Geheel getal | Idem, Bachelor in de LG-sector. `-1` wordt `null` met vlag `AantalBekostigdeInschrijvingenBaLG_NVT`. |
| 18 | `AantalBekostigdeInschrijvingenMa` | Nee | Geheel getal | Idem, Master. `-1` wordt `null` met vlag `AantalBekostigdeInschrijvingenMa_NVT`. |
| 19 | `AantalBekostigdeInschrijvingenMaLG` | Nee | Geheel getal | Idem, Master in de LG-sector. `-1` wordt `null` met vlag `AantalBekostigdeInschrijvingenMaLG_NVT`. |
| 20 | `AantalBekostigdeInschrijvingenBaLGnaGraadBaMa` | Nee | Geheel getal | Idem, Bachelor in de LG-sector na een behaalde Bachelor- of Mastergraad. Het PvE zegt alleen 'idem'; de omschrijving volgt de veldnaam. `-1` wordt `null` met vlag `AantalBekostigdeInschrijvingenBaLGnaGraadBaMa_NVT`. |
| 21 | `AantalBekostigdeInschrijvingenMaLGnaGraadMa` | Nee | Geheel getal | Idem, Master in de LG-sector na een behaalde Mastergraad. Het PvE zegt alleen 'idem'; de omschrijving volgt de veldnaam. `-1` wordt `null` met vlag `AantalBekostigdeInschrijvingenMaLGnaGraadMa_NVT`. |

**Voorbeeld:**

```
BLB|700000001|800000001|||||||1|3|3|2|3|2|0|1|3|3|1|3||||
```

!!! note "Verplicht en n.v.t."
    Volgens het PvE zijn de tellers verplicht. Ze kunnen `-1` zijn (*n.v.t.*: er kan voor
    die categorie geen deelname meer bekostigd worden door een eerder behaalde graad).
    De decoder zet `-1` om naar `null` en legt dat vast in een `_NVT`-vlag; daarom
    meldt de validatie een lege teller niet als ontbrekend veld. De `_NVT`-vlag staat in de
    brondata en in `fact_loopbaan`.

!!! warning "Alleen de huidige BLB-versie"
    Het PvE beschrijft twee BLB-versies. Deze tool ondersteunt de versie **met**
    `DatumGraadBehaaldAD`/`ADLG` en de `Verbruik…`-velden (in het PvE "Nieuwe versie").
    De oude versie (vóór september 2019, bestandsnaam met `_OUD`) wordt niet herkend: de
    app meldt zo'n bestand als *niet herkend en overgeslagen*. Zie [PvE-versies](../pve-wijzigingen.md#blb-versies).
    Door het opvullen met lege velden is de versie niet aan het aantal velden te herkennen.

Het BLB-record wordt gebruikt voor [`fact_loopbaan`](../datamodel.md#fact_loopbaan) en de
graaddatums in [`dim_persoon`](../datamodel.md#dim_persoon).
