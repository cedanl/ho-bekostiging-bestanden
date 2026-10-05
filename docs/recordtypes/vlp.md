# VLP – Voorlooprecord

Het eerste record van elk bestand. Het zegt voor welke instelling het bestand is,
voor welk bekostigingsjaar en wanneer het is aangemaakt. Er is precies één VLP per
bestand; een ander aantal geeft de melding *Eén rij*.

## Analysebestand (VLPBEK en DEFBEK)

| Pos | Veld | Verplicht | Type | Definitie |
|---|---|---|---|---|
| 1 | `Recordsoort` | Ja | Tekst | Aanduiding van het record; altijd de recordcode van deze pagina. |
| 2 | `BRIN` | Ja | Tekst | Instellingscode: 2 cijfers gevolgd door 2 hoofdletters. |
| 3 | `Bekostigingsjaar` | Ja | Geheel getal | Begrotingsjaar waarin de bekostiging wordt uitgekeerd aan de instellingen. |
| 4 | `DatumAanmaak` | Ja | Datum (`jjjjmmdd`) | Datum waarop het bestand is aangemaakt. |

**Voorbeeld:**

```
VLP|99XX|2025|20240715|||||||||||||||||||||
```

## Historisch bestand (HISBEK)

In HISBEK heeft het VLP-record **geen** `Bekostigingsjaar`: dat staat per HRD- en
HRR-record. Het jaar in de bestandsnaam is het laatste bekostigingsjaar in het bestand.

| Pos | Veld | Verplicht | Type | Definitie |
|---|---|---|---|---|
| 1 | `Recordsoort` | Ja | Tekst | Aanduiding van het record; altijd de recordcode van deze pagina. |
| 2 | `BRIN` | Ja | Tekst | Instellingscode: 2 cijfers gevolgd door 2 hoofdletters. |
| 3 | `DatumAanmaak` | Ja | Datum (`jjjjmmdd`) | Datum waarop het bestand is aangemaakt. |

**Voorbeeld:**

```
VLP|99XX|20250301||||||||||||||||||||||
```

## Controles

- De `BRIN` in de bestandsnaam moet gelijk zijn aan die in het VLP (anders een *error*).
- Het `Bekostigingsjaar` in de bestandsnaam moet gelijk zijn aan dat in het VLP
  (anders een *warning*; het VLP is leidend).
- Ontbreekt het VLP, dan wordt het bestand niet verwerkt.

Zie [Kwaliteit](../kwaliteit.md).
