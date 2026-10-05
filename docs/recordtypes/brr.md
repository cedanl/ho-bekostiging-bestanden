# BRR – Bekostigingsresultaat resultaat

Eén record per **resultaat** (behaalde graad) met het resultaat van de bepaling van de
bekostigingsstatus, voor de in het bekostigingsjaar beoordeelde resultaten. Dat kunnen
ook resultaten bij andere instellingen zijn.

Alleen in het analysebestand (VLPBEK en DEFBEK). In HISBEK heet dit record [HRR](hrr.md).

| Pos | Veld | Verplicht | Type | Definitie |
|---|---|---|---|---|
| 1 | `Recordsoort` | Ja | Tekst | Aanduiding van het record; altijd de recordcode van deze pagina. |
| 2 | `Burgerservicenummer` | Nee | Tekst | BSN van de student, 9 tekens (indien nodig met voorloopnul). Leeg als de student alleen een onderwijsnummer heeft. |
| 3 | `Onderwijsnummer` | Nee | Tekst | Nummer voor een student zonder (verifieerbaar) BSN, 9 tekens (indien nodig met voorloopnul). |
| 4 | `BRIN` | Ja | Tekst | Instellingscode: 2 cijfers gevolgd door 2 hoofdletters. |
| 5 | `Resultaatvolgnummer` | Ja | Tekst | Door de instelling toegekend volgnummer van het onderwijsresultaat, uniek per BRIN (cijfers en letters, max. 20 tekens). |
| 6 | `Bekostigingsindicatie` | Ja | `J`/`N` | Komt de inschrijving of graad in aanmerking voor bekostiging (rijksbijdrage)? `J` of `N`. |
| 7 | `CodeBekostigingstatus` | Ja | Tekst | Toelichting op de bekostiging: één of meer statuscodes in kleine letters, oplopend gesorteerd en gescheiden door komma's, bijvoorbeeld `na,ti`. Zie [Bekostigingstatus](../waardenlijsten.md#bekostigingstatus). |
| 8 | `Bekostigingsniveau` | Ja | Tekst | Niveau van de bekostiging: `LAAG`, `HOOG` of `TOP`. Zie [Bekostigingsniveau](../waardenlijsten.md#bekostigingsniveau). |
| 9 | `JointDegreeFactor` | Nee | Decimaal getal | Gewicht van de graad voor de bekostiging: een single degree telt als 1, een joint degree naar rato van het aantal Nederlandse instellingen in het samenwerkingsverband. |
| 10 | `Opleidingscode` | Ja | Tekst | Opleidingscode volgens de ISAT-codering, 5 tekens (met voorloopnul als de code kleiner is dan 10000). |
| 11 | `Opleidingsniveau` | Ja | Tekst | Opleidingsniveau voor het hoger onderwijs, bijvoorbeeld `HBO-BA`. Zie [Opleidingsniveau](../waardenlijsten.md#opleidingsniveau). |
| 12 | `Opleidingsfase` | Ja | Tekst | Aanduiding van het deel van de opleiding, bijvoorbeeld `B` (bachelor) of `M` (master). Zie [Opleidingsfase](../waardenlijsten.md#opleidingsfase). |
| 13 | `EersteGraad` | Ja | `J`/`N` | Moet het onderwijsresultaat voor de bekostiging worden meegenomen? `J` of `N`. Voor een propedeutische graad altijd `N`. |
| 14 | `DatumDiploma` | Ja | Datum (`jjjjmmdd`) | Datum waarop de student de graad heeft behaald. |
| 15 | `Onderwijsvorm` | Ja | Tekst | Voltijd, deeltijd of duaal. Zie [Onderwijsvorm](../waardenlijsten.md#onderwijsvorm). |
| 16 | `DatumEersteAanlevering` | Ja | Datum (`jjjjmmdd`) | Datum waarop de inschrijving of graad voor het eerst bij DUO is ontvangen. |
| 17 | `OpleidingOnderdeel` | Nee | Tekst | Onderdeel van het hoger onderwijs waar de opleiding bij hoort, bijvoorbeeld `TECHNIEK`. Zie [Opleidingonderdeel](../waardenlijsten.md#opleidingonderdeel). |
| 18 | `Bekostigingscode` | Nee | Tekst | Is er sprake van bekostiging: `BEKOSTIGD` of `OPEN_BESTEL` (experiment). Zie [Bekostigingscode](../waardenlijsten.md#bekostigingscode). |
| 19 | `IndicatieSectorLG` | Nee | `J`/`N` | Betreft het een opleiding in de LG-sector? `J` of `N`. |
| 20 | `IndicatieBaMa` | Nee | Tekst | Hoe de deelname of het resultaat meetelt voor de bekostigingsstatus (bachelor, master, …). Zie [Indicatie Ba/Ma](../waardenlijsten.md#indicatie-bama). |
| 21 | `IndicatieAcademischZiekenhuis` | Nee | `J`/`N` | Betreft het een opleiding aan een academisch ziekenhuis? `J` of `N`. |
| 22 | `IndicatieGraadTeltVoorBekostigingsloopbaan` | Ja | `J`/`N` | Wordt de graad opgenomen in de bekostigingsloopbaan van de student? `J` of `N`. |
| 23 | `IndicatieNationaliteitsvoorwaardeSF` | Ja | `J`/`N` | Voldoet de student aan de nationaliteitsvoorwaarde of verblijfsvergunning uit artikel 2.2, eerste lid, van de WSF? `J` of `N`. Bij beoordeelde deelnames altijd gevuld. |
| 24 | `IndicatieGBARelatie` | Ja | `J`/`N` | Is er voor de persoon een relatie met de BRP? `J` of `N`. |

**Voorbeeld:**

```
BRR|700000008|800000008|99XX|R000082023|J|pg|LAAG|1|56001|WO-BA|B|J|20230625|VT|20230715|RECHT|BEKOSTIGD|N|B|N|J|J|J|
```

Het record wordt gebruikt voor [`fact_resultaat`](../datamodel.md#fact_resultaat). BRR heeft
geen eigen bekostigingsjaar: dat komt uit het VLP.
