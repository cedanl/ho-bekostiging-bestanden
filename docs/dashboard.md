# Dashboard

Het dashboard laat zien **wat er bekostigd wordt en waarom niet**, voor de eigen instelling.
De berekeningen staan in `indicatoren.py` (pure functies op het star schema); de app toont
alleen. Elke grafiek heeft in de app een uitklapbare toelichting.

![Dashboard — bekostigingstrechter](assets/dashboard.png)

## Filters

| Filter | Keuze |
|---|---|
| Levering | Definitief (DEFBEK) of Voorlopig (VLPBEK) |
| Bekostigingsjaar | De jaren waarvoor een levering is verwerkt |
| Opleidingsniveau | Alle niveaus, of een selectie (bijvoorbeeld `HBO-BA`) |

Alle cijfers gaan over de **eigen instelling** (`dim_instelling.EigenInstelling`). Deelnames
en resultaten van dezelfde studenten bij andere instellingen staan in de bestanden, maar tellen
hier niet mee.

## De vijf tabs

### Trechter

Aantallen deelnames en graden in drie stappen:

| Stap | Betekenis |
|---|---|
| In bestand | Alle rijen van de eigen instelling in de gekozen levering |
| Beoordeeld | Zonder status `mv` |
| Bekostigd | Beoordeeld én bekostigingsindicatie `J` |

!!! warning "Nog te bevestigen"
    Dat `mv` de juiste afbakening is voor *beoordeeld* is een aanname op basis van PvE §17.5:
    deelnames met status `mv` vallen buiten de beoordeling en neemt DUO alleen op voor het
    complete beeld van de student. Laat dit bevestigen door iemand met
    HO-bekostigingskennis.

### Waarom niet bekostigd

Van de beoordeelde, niet-bekostigde rijen wordt elke statuscode apart geteld, gegroepeerd
naar [statusgroep](waardenlijsten.md#bekostigingstatus). Een deelname met `na,ti` telt bij
beide codes. Codes die *wel bekostigd* betekenen vallen weg. De omschrijving staat erbij in
gewone taal.

!!! note
    De groepen (zoals *Aanlevering* of *Verbruik en limieten*) zijn een eigen indeling van
    deze repo, niet van DUO.

### Per opleiding

Per opleidingscode: het aantal beoordeelde deelnames en het aandeel dat bekostigd is.

### Voorlopig vs definitief

Welke deelnames veranderden van status tussen de voorlopige en de definitieve bepaling. Per
bekostigingsjaar wordt de nieuwste VLPBEK naast de nieuwste DEFBEK gelegd. Deelnames worden
gekoppeld op jaar, BRIN, inschrijvingvolgnummer en persoon; alleen deelnames waarvan de
statuscode veranderde worden getoond.

Deze tab werkt alleen voor jaren waarvoor **zowel** een VLPBEK als een DEFBEK is verwerkt.

### Historie

Per bekostigingsjaar het aantal beoordeelde deelnames en graden en hoeveel daarvan bekostigd
zijn, uit het HISBEK-bestand. Net als de trechter telt dit alleen beoordeelde rijen. Deze tab
is alleen zichtbaar als er een HISBEK-bestand is verwerkt; anders staat er een korte uitleg.

## Voor ontwikkelaars

Wijzig je een grafiek in `app/pages/dashboard.py`, werk dan ook de toelichting in
`app/_chart_docs.py` en deze pagina bij. Een grafiek zonder toelichting is niet af.
