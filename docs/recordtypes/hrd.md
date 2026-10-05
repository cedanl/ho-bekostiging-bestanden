# HRD – Historisch resultaat deelname

Eén record per deelname die **in het verleden** is beoordeeld, voor alle definitieve
bekostigingsjaren. Het lijkt op [BRD](brd.md), met een eigen `Bekostigingsjaar` per record
en een paar extra velden (ECTS voor de Open Universiteit, en oude velden die alleen in 2011
t/m 2014 gevuld zijn). Alleen in het historische bestand (HISBEK).

De inschrijvingsvorm kent hier ook `A` (auditor) en `T` (toegelaten student). Het
`Inschrijvingvolgnummer` is in HRD niet verplicht, daarom krijgt elke feitrij in het star
schema een eigen `_feit_id`.

| Pos | Veld | Verplicht | Type | Definitie |
|---|---|---|---|---|
| 1 | `Recordsoort` | Ja | Tekst | Aanduiding van het record; altijd de recordcode van deze pagina. |
| 2 | `Burgerservicenummer` | Nee | Tekst | BSN van de student, 9 tekens (indien nodig met voorloopnul). Leeg als de student alleen een onderwijsnummer heeft. |
| 3 | `Onderwijsnummer` | Nee | Tekst | Nummer voor een student zonder (verifieerbaar) BSN, 9 tekens (indien nodig met voorloopnul). |
| 4 | `Bekostigingsjaar` | Ja | Geheel getal | Begrotingsjaar waarin de bekostiging wordt uitgekeerd aan de instellingen. |
| 5 | `BRIN` | Ja | Tekst | Instellingscode: 2 cijfers gevolgd door 2 hoofdletters. |
| 6 | `Inschrijvingvolgnummer` | Nee | Tekst | Door de instelling toegekend volgnummer van de inschrijving, uniek per BRIN (cijfers en letters, max. 20 tekens). |
| 7 | `Bekostigingsindicatie` | Ja | `J`/`N` | Komt de inschrijving of graad in aanmerking voor bekostiging (rijksbijdrage)? `J` of `N`. |
| 8 | `CodeBekostigingstatus` | Ja | Tekst | Toelichting op de bekostiging: één of meer statuscodes in kleine letters, oplopend gesorteerd en gescheiden door komma's, bijvoorbeeld `na,ti`. Zie [Bekostigingstatus](../waardenlijsten.md#bekostigingstatus). |
| 9 | `Bekostigingsniveau` | Nee | Tekst | Niveau van de bekostiging: `LAAG`, `HOOG` of `TOP`. Zie [Bekostigingsniveau](../waardenlijsten.md#bekostigingsniveau). |
| 10 | `Opleidingscode` | Ja | Tekst | Opleidingscode volgens de ISAT-codering, 5 tekens (met voorloopnul als de code kleiner is dan 10000). |
| 11 | `Opleidingsniveau` | Ja | Tekst | Opleidingsniveau voor het hoger onderwijs, bijvoorbeeld `HBO-BA`. Zie [Opleidingsniveau](../waardenlijsten.md#opleidingsniveau). |
| 12 | `Opleidingsfase` | Ja | Tekst | Aanduiding van het deel van de opleiding, bijvoorbeeld `B` (bachelor) of `M` (master). Zie [Opleidingsfase](../waardenlijsten.md#opleidingsfase). |
| 13 | `DatumInschrijving` | Ja | Datum (`jjjjmmdd`) | Datum waarop de student is ingeschreven. |
| 14 | `DatumUitschrijving` | Ja | Datum (`jjjjmmdd`) | Datum tot wanneer de inschrijving loopt. |
| 15 | `EersteInschrijving` | Ja | `J`/`N` | Is dit de opleiding van eerste inschrijving van de student? `J` of `N`. Bij meerdere eerste inschrijvingen bepalen de instellingen onderling welke dat is; voor het schakelprogramma altijd `N`. |
| 16 | `Inschrijvingsvorm` | Ja | Tekst | Vorm waarin de student de opleiding wil volgen. Zie [Inschrijvingsvorm (HISBEK)](../waardenlijsten.md#inschrijvingsvorm-hisbek). |
| 17 | `Onderwijsvorm` | Ja | Tekst | Voltijd, deeltijd of duaal. Zie [Onderwijsvorm](../waardenlijsten.md#onderwijsvorm). |
| 18 | `DatumEersteAanlevering` | Nee | Datum (`jjjjmmdd`) | Datum waarop de inschrijving of graad voor het eerst bij DUO is ontvangen. |
| 19 | `Bekostigingsduur` | Nee | Geheel getal | Maximale duur van een bekostiging in maanden (0 t/m 99). |
| 20 | `ECTS` | Nee | Decimaal getal | Studielast in ECTS. Alleen gevuld voor deelnames van de Open Universiteit vanaf 2015. |
| 21 | `ECTSBekostigd` | Nee | Decimaal getal | Aantal bekostigde ECTS. Alleen gevuld voor deelnames van de Open Universiteit vanaf 2015. |
| 22 | `OpleidingOnderdeel` | Nee | Tekst | Onderdeel van het hoger onderwijs waar de opleiding bij hoort, bijvoorbeeld `TECHNIEK`. Zie [Opleidingonderdeel](../waardenlijsten.md#opleidingonderdeel). |
| 23 | `Bekostigingscode` | Nee | Tekst | Is er sprake van bekostiging: `BEKOSTIGD` of `OPEN_BESTEL` (experiment). Zie [Bekostigingscode](../waardenlijsten.md#bekostigingscode). |
| 24 | `IndicatieSectorLG` | Nee | `J`/`N` | Betreft het een opleiding in de LG-sector? `J` of `N`. |
| 25 | `IndicatieBaMa` | Nee | Tekst | Hoe de deelname of het resultaat meetelt voor de bekostigingsstatus (bachelor, master, …). Zie [Indicatie Ba/Ma](../waardenlijsten.md#indicatie-bama). |
| 26 | `IndicatieAcademischZiekenhuis` | Nee | `J`/`N` | Betreft het een opleiding aan een academisch ziekenhuis? `J` of `N`. |
| 27 | `DuitseDeelstaat` | Nee | Tekst | Code van de Duitse deelstaat waar de student woonde. Gevuld van 2011 t/m 2014, anders leeg. |
| 28 | `IndicatieWoonplaatsVereiste` | Nee | `J`/`N` | Voldoet de persoon aan de woonplaatsvereiste? `J` of `N`. Gevuld van 2011 t/m 2014. |
| 29 | `IndicatieNationaliteitsvoorwaardeSF` | Ja | `J`/`N` | Voldoet de student aan de nationaliteitsvoorwaarde of verblijfsvergunning uit artikel 2.2, eerste lid, van de WSF? `J` of `N`. Bij beoordeelde deelnames altijd gevuld. |
| 30 | `IndicatieGBARelatie` | Nee | `J`/`N` | Is er voor de persoon een relatie met de BRP? `J` of `N`. |

**Voorbeeld:**

```
HRD|700000001|800000001|2023|99XX|99XX000012021|J|pi|HOOG|34001|HBO-BA|B|20210901|20220831|J|S|VT|20210915|12|||TECHNIEK|BEKOSTIGD|N|B|N|||J|J
```

Het record wordt gebruikt voor [`fact_deelname`](../datamodel.md#fact_deelname), samen met BRD.
