# BRD – Bekostigingsresultaat deelname

Eén record per **deelname** (inschrijving) met het resultaat van de bepaling van de
bekostigingsstatus. Het bevat alle deelnames die in het bekostigingsjaar zijn beoordeeld.
Daarnaast neemt DUO deelnames op die buiten de beoordeling vallen; die krijgen de status
`mv`, zodat alle inschrijvingen van de student in de periode 2 oktober van
bekostigingsjaar − 3 t/m 1 oktober van bekostigingsjaar − 2 in het bestand staan. Dat
kunnen ook inschrijvingen bij **andere instellingen** zijn.

Alleen in het analysebestand (VLPBEK en DEFBEK). In HISBEK heet dit record [HRD](hrd.md).

| Pos | Veld | Verplicht | Type | Definitie |
|---|---|---|---|---|
| 1 | `Recordsoort` | Ja | Tekst | Aanduiding van het record; altijd de recordcode van deze pagina. |
| 2 | `Burgerservicenummer` | Nee | Tekst | BSN van de student, 9 tekens (indien nodig met voorloopnul). Leeg als de student alleen een onderwijsnummer heeft. |
| 3 | `Onderwijsnummer` | Nee | Tekst | Nummer voor een student zonder (verifieerbaar) BSN, 9 tekens (indien nodig met voorloopnul). |
| 4 | `BRIN` | Ja | Tekst | Instellingscode: 2 cijfers gevolgd door 2 hoofdletters. |
| 5 | `Inschrijvingvolgnummer` | Ja | Tekst | Door de instelling toegekend volgnummer van de inschrijving, uniek per BRIN (cijfers en letters, max. 20 tekens). |
| 6 | `Bekostigingsindicatie` | Ja | `J`/`N` | Komt de inschrijving of graad in aanmerking voor bekostiging (rijksbijdrage)? `J` of `N`. |
| 7 | `CodeBekostigingstatus` | Ja | Tekst | Toelichting op de bekostiging: één of meer statuscodes in kleine letters, oplopend gesorteerd en gescheiden door komma's, bijvoorbeeld `na,ti`. Zie [Bekostigingstatus](../waardenlijsten.md#bekostigingstatus). |
| 8 | `Bekostigingsniveau` | Nee | Tekst | Niveau van de bekostiging: `LAAG`, `HOOG` of `TOP`. Zie [Bekostigingsniveau](../waardenlijsten.md#bekostigingsniveau). |
| 9 | `Opleidingscode` | Ja | Tekst | Opleidingscode volgens de ISAT-codering, 5 tekens (met voorloopnul als de code kleiner is dan 10000). |
| 10 | `Opleidingsniveau` | Ja | Tekst | Opleidingsniveau voor het hoger onderwijs, bijvoorbeeld `HBO-BA`. Zie [Opleidingsniveau](../waardenlijsten.md#opleidingsniveau). |
| 11 | `Opleidingsfase` | Ja | Tekst | Aanduiding van het deel van de opleiding, bijvoorbeeld `B` (bachelor) of `M` (master). Zie [Opleidingsfase](../waardenlijsten.md#opleidingsfase). |
| 12 | `DatumInschrijving` | Ja | Datum (`jjjjmmdd`) | Datum waarop de student is ingeschreven. |
| 13 | `DatumUitschrijving` | Ja | Datum (`jjjjmmdd`) | Datum tot wanneer de inschrijving loopt. |
| 14 | `EersteInschrijving` | Ja | `J`/`N` | Is dit de opleiding van eerste inschrijving van de student? `J` of `N`. Bij meerdere eerste inschrijvingen bepalen de instellingen onderling welke dat is; voor het schakelprogramma altijd `N`. |
| 15 | `Inschrijvingsvorm` | Ja | Tekst | Vorm waarin de student de opleiding wil volgen. Zie [Inschrijvingsvorm](../waardenlijsten.md#inschrijvingsvorm). |
| 16 | `Onderwijsvorm` | Ja | Tekst | Voltijd, deeltijd of duaal. Zie [Onderwijsvorm](../waardenlijsten.md#onderwijsvorm). |
| 17 | `DatumEersteAanlevering` | Ja | Datum (`jjjjmmdd`) | Datum waarop de inschrijving of graad voor het eerst bij DUO is ontvangen. |
| 18 | `Bekostigingsduur` | Nee | Geheel getal | Maximale duur van een bekostiging in maanden (0 t/m 99). |
| 19 | `OpleidingOnderdeel` | Nee | Tekst | Onderdeel van het hoger onderwijs waar de opleiding bij hoort, bijvoorbeeld `TECHNIEK`. Zie [Opleidingonderdeel](../waardenlijsten.md#opleidingonderdeel). |
| 20 | `Bekostigingscode` | Nee | Tekst | Is er sprake van bekostiging: `BEKOSTIGD` of `OPEN_BESTEL` (experiment). Zie [Bekostigingscode](../waardenlijsten.md#bekostigingscode). |
| 21 | `IndicatieSectorLG` | Nee | `J`/`N` | Betreft het een opleiding in de LG-sector? `J` of `N`. |
| 22 | `IndicatieBaMa` | Nee | Tekst | Hoe de deelname of het resultaat meetelt voor de bekostigingsstatus (bachelor, master, …). Zie [Indicatie Ba/Ma](../waardenlijsten.md#indicatie-bama). |
| 23 | `IndicatieAcademischZiekenhuis` | Nee | `J`/`N` | Betreft het een opleiding aan een academisch ziekenhuis? `J` of `N`. |
| 24 | `IndicatieNationaliteitsvoorwaardeSF` | Nee | `J`/`N` | Voldoet de student aan de nationaliteitsvoorwaarde of verblijfsvergunning uit artikel 2.2, eerste lid, van de WSF? `J` of `N`. Bij beoordeelde deelnames altijd gevuld. |
| 25 | `IndicatieGBARelatie` | Nee | `J`/`N` | Is er voor de persoon een relatie met de BRP? `J` of `N`. |

**Voorbeeld:**

```
BRD|700000001|800000001|99XX|99XX000012023|J|pi|HOOG|34001|HBO-BA|B|20230901|20240831|J|S|VT|20230915|12|TECHNIEK|BEKOSTIGD|N|B|N|J|J
```

Het record wordt gebruikt voor [`fact_deelname`](../datamodel.md#fact_deelname); de
statuscodes komen via [`fact_status`](../datamodel.md#fact_status) in een eigen tabel.
BRD heeft geen eigen bekostigingsjaar: dat komt uit het VLP.
