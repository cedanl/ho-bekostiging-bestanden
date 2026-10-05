# SLR – Sluitrecord

Het laatste record van elk bestand, met het aantal records per recordsoort. De tool
vergelijkt die aantallen met wat er werkelijk is ingelezen (controle *Aantal records*);
een verschil is een *error* en wijst op een afgekapt of beschadigd bestand.

## Analysebestand (VLPBEK en DEFBEK)

| Pos | Veld | Verplicht | Type | Definitie |
|---|---|---|---|---|
| 1 | `Recordsoort` | Ja | Tekst | Aanduiding van het record; altijd de recordcode van deze pagina. |
| 2 | `AantalBLBrecords` | Ja | Geheel getal | Aantal BLB-records in het bestand. |
| 3 | `AantalBRDrecords` | Ja | Geheel getal | Aantal BRD-records in het bestand. |
| 4 | `AantalBRRrecords` | Ja | Geheel getal | Aantal BRR-records in het bestand. |

**Voorbeeld:**

```
SLR|150|164|47|||||||||||||||||||||
```

## Historisch bestand (HISBEK)

| Pos | Veld | Verplicht | Type | Definitie |
|---|---|---|---|---|
| 1 | `Recordsoort` | Ja | Tekst | Aanduiding van het record; altijd de recordcode van deze pagina. |
| 2 | `AantalHRDrecords` | Ja | Geheel getal | Aantal HRD-records in het bestand. |
| 3 | `AantalHRRrecords` | Ja | Geheel getal | Aantal HRR-records in het bestand. |

**Voorbeeld:**

```
SLR|400|30||||||||||||||||||||||
```

Zie [Kwaliteit](../kwaliteit.md).
