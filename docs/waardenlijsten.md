# Waardenlijsten

De codelijsten staan als CSV in `src/ho_bekostiging_bestanden/metadata/`. De validatie
controleert elk veld met een lijst (zie het schema, `codelijsten`); een onbekende code
geeft een *warning*, geen *error*.

## Bekostigingstatus

Het veld `CodeBekostigingstatus` bevat één of meer van deze codes (kleine letters,
oplopend gesorteerd, gescheiden door komma's, bijvoorbeeld `na,ti`). De bron is
PvE §19.7.5. In het star schema staan ze in
[`dim_status`](datamodel.md#dim_status); elke code van een deelname of resultaat staat als
eigen rij in [`fact_status`](datamodel.md#fact_status).

Er zijn 34 codes. De codes `pi`, `pd`, `pg`, `pb`, `pm` en `po` betekenen *wel
bekostigd*; alle andere betekenen *niet bekostigd*.

!!! warning "Groepen zijn een eigen indeling"
    De omschrijvingen komen uit het PvE. De **groepen** (zoals *Verbruik en limieten*) zijn
    een indeling van deze repo, niet van DUO, en nog te bevestigen door iemand met
    HO-bekostigingskennis. Ze worden alleen gebruikt om redenen in het dashboard te
    ordenen.

### Wel bekostigd

| Code | Betekenis | Bekostigd |
|---|---|---|
| `pi` | De inschrijving wordt bekostigd | Ja |
| `pd` | De inschrijving wordt deels bekostigd | Ja |
| `pg` | De graad wordt bekostigd | Ja |
| `pb` | Ongedeelde opleiding: alleen de (impliciete) BA-graad wordt bekostigd, niet de MA-graad | Ja |
| `pm` | Ongedeelde opleiding: alleen de MA-graad wordt bekostigd, niet de (impliciete) BA-graad | Ja |
| `po` | Ongedeelde opleiding: zowel de (impliciete) BA- als de MA-graad wordt bekostigd | Ja |

### Status van de student

| Code | Betekenis | Bekostigd |
|---|---|---|
| `ex` | Het betreft een extraneus-inschrijving | Nee |
| `jk` | Meerdere eerste inschrijvingen aangeleverd voor verschillende opleidingen | Nee |
| `jl` | Geen opleiding van eerste inschrijving (eerste inschrijving is N) | Nee |
| `jm` | Meerdere eerste inschrijvingen voor dezelfde opleiding aan dezelfde instelling | Nee |
| `na` | De student voldoet niet aan het woonplaatsvereiste | Nee |
| `nr` | De student voldoet niet aan het nationaliteitsvereiste | Nee |

### Verbruik en limieten

| Code | Betekenis | Bekostigd |
|---|---|---|
| `nb` | Niet bekostigd i.v.m. eerder behaalde graad/graden | Nee |
| `nd` | De student heeft al eerder een MA-graad behaald | Nee |
| `nf` | Maximaal aantal bekostigde inschrijvingen overschreden (rekening houdend met eerdere graden) | Nee |
| `ng` | Maximaal aantal bekostigde inschrijvingen overschreden (nog geen graad behaald) | Nee |
| `nh` | Ongedeelde opleiding: toegestane te bekostigen jaren MA verbruikt | Nee |
| `ni` | Ongedeelde opleiding: toegestane jaren MA in een uitzonderingscategorie verbruikt | Nee |
| `nk` | Toegestane te bekostigen jaren of studielast MA verbruikt | Nee |

### Graad-specifiek

| Code | Betekenis | Bekostigd |
|---|---|---|
| `ne` | Geen voor bekostiging relevante graad of een AD-graad | Nee |
| `np` | Graad die niet voor bekostiging in aanmerking komt (opleidingsfase P of D of A) | Nee |
| `ns` | Aan verschillende instellingen op dezelfde dag een zelfde soort graad behaald | Nee |
| `nt` | Meerdere graden aan dezelfde instelling, slechts één wordt bekostigd | Nee |
| `no` | Ongedeelde opleiding waarvan de behaalde graden (BA en MA) beide niet bekostigd worden | Nee |

### Tijdvak

| Code | Betekenis | Bekostigd |
|---|---|---|
| `mt` | De graad is behaald na de peilperiode | Nee |
| `mu` | De graad is behaald vóór de peilperiode | Nee |
| `mv` | De inschrijving is niet geldig op de peildatum / valt buiten het bekostigingsjaar | Nee |
| `mw` | Graad zonder bijbehorende op datum diploma geldige inschrijving | Nee |

### Opleiding

| Code | Betekenis | Bekostigd |
|---|---|---|
| `ob` | Datum diploma valt niet in de accreditatieperiode | Nee |
| `oc` | Het betreft geen geaccrediteerde opleiding | Nee |

### Aanlevering

| Code | Betekenis | Bekostigd |
|---|---|---|
| `ti` | De inschrijving is niet tijdig aangeleverd | Nee |
| `tg` | De graad is niet tijdig aangeleverd | Nee |
| `nl` | Aangeleverd met de markering om niet te bekostigen | Nee |

### Overig

| Code | Betekenis | Bekostigd |
|---|---|---|
| `nc` | Niet bekostigd vanuit de conversie naar HORS | Nee |

## Bekostigingsniveau

| Code | Omschrijving |
|---|---|
| `LAAG` | Laag |
| `HOOG` | Hoog |
| `TOP` | Top |

## Opleidingsniveau

| Code | Omschrijving |
|---|---|
| `HBO-AD` | HBO Associate Degree |
| `HBO-BA` | HBO Bachelor |
| `HBO-MA` | HBO Master |
| `HBO-O` | HBO Ongedeeld |
| `WO-BA` | WO Bachelor |
| `WO-MA` | WO Master |
| `WO-O` | WO Ongedeeld |

## Opleidingsfase

| Code | Omschrijving |
|---|---|
| `1` | Eerste fase |
| `2` | Tweede fase |
| `A` | Associate Degree |
| `B` | Bachelor |
| `D` | Propedeuse bachelor |
| `I` | Initiële opleiding |
| `K` | Kandidaats |
| `L` | Universitaire lerarenopleiding (ULO) |
| `M` | Master |
| `P` | Propedeuse |
| `S` | Schakelprogramma |
| `T` | Tussentijds doctoraal examen |
| `V` | Vervolg of voortgezette opleiding |
| `W` | Voortgezette opleiding |

## Inschrijvingsvorm

Voor het analysebestand (BRD):

| Code | Omschrijving |
|---|---|
| `E` | Extraneus |
| `S` | Student |

## Inschrijvingsvorm (HISBEK)

Voor het historische bestand (HRD) komen daar `A` en `T` bij:

| Code | Omschrijving |
|---|---|
| `A` | Auditor |
| `E` | Extraneus |
| `S` | Student |
| `T` | Toegelaten student |

## Onderwijsvorm

| Code | Omschrijving |
|---|---|
| `VT` | Voltijd |
| `DT` | Deeltijd |
| `DU` | Duaal |

## Opleidingonderdeel

| Code | Omschrijving |
|---|---|
| `ECONOMIE` | Economie |
| `GEDRAG_EN_MAATSCHAPPIJ` | Gedrag en maatschappij |
| `GEZONDHEIDSZORG` | Gezondheidszorg |
| `LANDBOUW_EN_NATUURLIJKE_OMGEVING` | Landbouw en natuurlijke omgeving |
| `NATUUR` | Natuur |
| `ONDERWIJS` | Onderwijs |
| `RECHT` | Recht |
| `SECTOROVERSTIJGEND` | Sectoroverstijgend |
| `TAAL_EN_CULTUUR` | Taal en cultuur |
| `TECHNIEK` | Techniek |

## Bekostigingscode

| Code | Omschrijving |
|---|---|
| `BEKOSTIGD` | Bekostigd |
| `OPEN_BESTEL` | Open bestel (experiment) |

## Indicatie Ba/Ma

| Code | Omschrijving |
|---|---|
| `B` | Bachelor |
| `M` | Master |
| `A` | Master met impliciete bachelor |
| `D` | Associate Degree |
