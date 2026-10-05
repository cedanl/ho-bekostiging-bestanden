# HRR – Historisch resultaat resultaat

Eén record per graad die **in het verleden** is beoordeeld, met een eigen `Bekostigingsjaar`
per record. Het lijkt op [BRR](brr.md). Een graad zonder `DatumDiploma` neemt DUO niet op.
Alleen in het historische bestand (HISBEK).

| Pos | Veld | Verplicht | Type | Definitie |
|---|---|---|---|---|
| 1 | `Recordsoort` | Ja | Tekst | Aanduiding van het record; altijd de recordcode van deze pagina. |
| 2 | `Burgerservicenummer` | Nee | Tekst | BSN van de student, 9 tekens (indien nodig met voorloopnul). Leeg als de student alleen een onderwijsnummer heeft. |
| 3 | `Onderwijsnummer` | Nee | Tekst | Nummer voor een student zonder (verifieerbaar) BSN, 9 tekens (indien nodig met voorloopnul). |
| 4 | `Bekostigingsjaar` | Ja | Geheel getal | Begrotingsjaar waarin de bekostiging wordt uitgekeerd aan de instellingen. |
| 5 | `BRIN` | Ja | Tekst | Instellingscode: 2 cijfers gevolgd door 2 hoofdletters. |
| 6 | `Resultaatvolgnummer` | Nee | Tekst | Door de instelling toegekend volgnummer van het onderwijsresultaat, uniek per BRIN (cijfers en letters, max. 20 tekens). |
| 7 | `Bekostigingsindicatie` | Ja | `J`/`N` | Komt de inschrijving of graad in aanmerking voor bekostiging (rijksbijdrage)? `J` of `N`. |
| 8 | `CodeBekostigingstatus` | Ja | Tekst | Toelichting op de bekostiging: één of meer statuscodes in kleine letters, oplopend gesorteerd en gescheiden door komma's, bijvoorbeeld `na,ti`. Zie [Bekostigingstatus](../waardenlijsten.md#bekostigingstatus). |
| 9 | `Bekostigingsniveau` | Nee | Tekst | Niveau van de bekostiging: `LAAG`, `HOOG` of `TOP`. Zie [Bekostigingsniveau](../waardenlijsten.md#bekostigingsniveau). |
| 10 | `JointDegreeFactor` | Ja | Decimaal getal | Gewicht van de graad voor de bekostiging: een single degree telt als 1, een joint degree naar rato van het aantal Nederlandse instellingen in het samenwerkingsverband. |
| 11 | `Opleidingscode` | Ja | Tekst | Opleidingscode volgens de ISAT-codering, 5 tekens (met voorloopnul als de code kleiner is dan 10000). |
| 12 | `Opleidingsniveau` | Ja | Tekst | Opleidingsniveau voor het hoger onderwijs, bijvoorbeeld `HBO-BA`. Zie [Opleidingsniveau](../waardenlijsten.md#opleidingsniveau). |
| 13 | `Opleidingsfase` | Ja | Tekst | Aanduiding van het deel van de opleiding, bijvoorbeeld `B` (bachelor) of `M` (master). Zie [Opleidingsfase](../waardenlijsten.md#opleidingsfase). |
| 14 | `EersteGraad` | Ja | `J`/`N` | Moet het onderwijsresultaat voor de bekostiging worden meegenomen? `J` of `N`. Voor een propedeutische graad altijd `N`. |
| 15 | `DatumDiploma` | Nee | Datum (`jjjjmmdd`) | Datum waarop de student de graad heeft behaald. |
| 16 | `Onderwijsvorm` | Ja | Tekst | Voltijd, deeltijd of duaal. Zie [Onderwijsvorm](../waardenlijsten.md#onderwijsvorm). |
| 17 | `DatumEersteAanlevering` | Nee | Datum (`jjjjmmdd`) | Datum waarop de inschrijving of graad voor het eerst bij DUO is ontvangen. |
| 18 | `OpleidingOnderdeel` | Nee | Tekst | Onderdeel van het hoger onderwijs waar de opleiding bij hoort, bijvoorbeeld `TECHNIEK`. Zie [Opleidingonderdeel](../waardenlijsten.md#opleidingonderdeel). |
| 19 | `Bekostigingscode` | Nee | Tekst | Is er sprake van bekostiging: `BEKOSTIGD` of `OPEN_BESTEL` (experiment). Zie [Bekostigingscode](../waardenlijsten.md#bekostigingscode). |
| 20 | `IndicatieSectorLG` | Nee | `J`/`N` | Betreft het een opleiding in de LG-sector? `J` of `N`. |
| 21 | `IndicatieBaMa` | Nee | Tekst | Hoe de deelname of het resultaat meetelt voor de bekostigingsstatus (bachelor, master, …). Zie [Indicatie Ba/Ma](../waardenlijsten.md#indicatie-bama). |
| 22 | `IndicatieAcademischZiekenhuis` | Nee | `J`/`N` | Betreft het een opleiding aan een academisch ziekenhuis? `J` of `N`. |
| 23 | `IndicatieGraadTeltVoorBekostigingsloopbaan` | Ja | `J`/`N` | Wordt de graad opgenomen in de bekostigingsloopbaan van de student? `J` of `N`. |
| 24 | `DuitseDeelstaat` | Nee | Tekst | Code van de Duitse deelstaat waar de student woonde. Gevuld van 2011 t/m 2014, anders leeg. |
| 25 | `IndicatieWoonplaatsVereiste` | Nee | `J`/`N` | Voldoet de persoon aan de woonplaatsvereiste? `J` of `N`. Gevuld van 2011 t/m 2014. |
| 26 | `IndicatieNationaliteitsvoorwaardeSF` | Ja | `J`/`N` | Voldoet de student aan de nationaliteitsvoorwaarde of verblijfsvergunning uit artikel 2.2, eerste lid, van de WSF? `J` of `N`. Bij beoordeelde deelnames altijd gevuld. |
| 27 | `IndicatieGBARelatie` | Nee | `J`/`N` | Is er voor de persoon een relatie met de BRP? `J` of `N`. |

**Voorbeeld:**

```
HRR|700000005|800000005|2024|99XX|R000052022|J|pg|HOOG|1|34001|HBO-BA|B|J|20220625|VT|20220715|TECHNIEK|BEKOSTIGD|N|B|N|J|||J|J
```

Het record wordt gebruikt voor [`fact_resultaat`](../datamodel.md#fact_resultaat), samen met BRR.
