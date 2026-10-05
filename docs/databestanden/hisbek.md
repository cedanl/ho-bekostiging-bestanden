# Historisch bestand (HISBEK)

Bron: PvE HO-instelling – DUO v26.3.1, bijlage 10 (§19).

## Doel en gebruik

Het bestand bevat de **historische bekostiging** voor één instelling: alle deelnames
(inschrijvingen) en resultaten (graden) die van belang zijn geweest voor **alle definitieve
bekostigingsjaren in het verleden**, met hun statussen. Net als het
[analysebestand](analysebestand.md) laat het zien wat bekostigd werd en, zo niet, waarom niet,
maar dan over meerdere jaren. Het is bedoeld voor analysedoeleinden.

## Bestandsnaam

```
HISBEK_2024_20250301_99XX.CSV
└──┬─┘ └┬─┘ └──┬───┘ └─┬┘
   │    │      │       └─ BRIN van de ontvanger
   │    │      └───────── aanmaakdatum (EEJJMMDD)
   │    └──────────────── laatste bekostigingsjaar in het bestand
   └───────────────────── HISBEK
```

## Opbouw

- Een voorlooprecord ([VLP](../recordtypes/vlp.md)). Anders dan in het analysebestand heeft dit
  **geen** bekostigingsjaar; dat staat per HRD- en HRR-record.
- Per student een setje records:
    - nul, één of meer [HRD](../recordtypes/hrd.md): alle bekostigingsresultaten van de in het
      verleden beoordeelde deelnames, ook bij andere instellingen;
    - nul, één of meer [HRR](../recordtypes/hrr.md): de beoordeelde resultaten. Een graad
      zonder `DatumDiploma` is niet opgenomen;
    - er is voor een student altijd minstens één HRD of HRR.
- Een sluitrecord ([SLR](../recordtypes/slr.md)) met het aantal HRD- en HRR-records.

Er is **geen BLB** in dit bestand.

## Sortering

HRD en HRR staan oplopend op burgerservicenummer (of onderwijsnummer, met studenten zonder
BSN achteraan) en daarbinnen **aflopend op bekostigingsjaar**.

## Verschillen met het analysebestand

| | VLPBEK / DEFBEK | HISBEK |
|---|---|---|
| Deelnames | BRD | HRD |
| Resultaten | BRR | HRR |
| Loopbaan | BLB | geen |
| Bekostigingsjaar | één, in het VLP | per record, in HRD en HRR |
| Inschrijvingsvorm | `E`, `S` | `A` (auditor), `E`, `S`, `T` (toegelaten student) |
| `Inschrijvingvolgnummer` | verplicht | niet verplicht |
| Extra velden | — | `ECTS`, `ECTSBekostigd` (alleen Open Universiteit vanaf 2015), `DuitseDeelstaat` en `IndicatieWoonplaatsVereiste` (alleen 2011 t/m 2014) |

HRD bevat per definitie alleen beoordeelde deelnames. Daarom is de nationaliteitsindicator
(`IndicatieNationaliteitsvoorwaardeSF`) in HRD altijd gevuld.

## Voorbeeld

```
VLP|99XX|20250301
HRD|700000001|800000001|2023|99XX|99XX000012021|J|pi|HOOG|34001|HBO-BA|B|20210901|20220831|J|S|VT|20210915|12|||TECHNIEK|BEKOSTIGD|N|B|N|||J|J
```

## Gebruik in het dashboard

De tab *Historie* van het [Dashboard](../dashboard.md) laat per bekostigingsjaar zien hoeveel
deelnames en graden bekostigd zijn. Die tab verschijnt alleen als er een HISBEK-bestand is
verwerkt.
