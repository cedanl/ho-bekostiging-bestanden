# Ontwerpkeuzes

De tool levert twee producten (zie [Home](index.md#wat-levert-de-tool-op)):

- **Brondata per levering** (`data/02-prepared/`): elk DUO-bestand per recordsoort, getrouw
  aan de levering. Hierin zitten alleen **technische** keuzes: typering en normalisatie van
  notaties.
- **Analysemodel** (`datamodel/`): de leveringen samengevoegd tot dimensies en feiten.
  Hierin zitten **inhoudelijke** keuzes: antwoorden op vragen die de bron zelf niet
  beantwoordt. Die keuzes staan hieronder, elk met een reden en een alternatief.

Wie het analysemodel gebruikt, neemt deze keuzes over. Wie een andere keuze wil, bouwt verder
op de brondata.

!!! note "Bijhouden"
    Elke wijziging die een keuze in het analysemodel toevoegt of verandert, werkt deze pagina
    bij.

!!! info "Nog te bevestigen"
    Keuzes met **[Te checken]** zijn aannames die een collega met HO-bekostigingskennis of
    DUO nog moet bevestigen. Ze staan ook in de ontwerp-spec in `docs/superpowers/specs/`.

## Brondata

| Keuze | Waarom | Alternatief | Gevolg | Code |
|---|---|---|---|---|
| **Veldindeling per recordsoort uit het PvE**, als TOML, positioneel | DUO-bestanden hebben geen kolomkoppen | Kolommen afleiden uit de data | Een nieuwe PvE-versie is een wijziging in `metadata/`, niet in code | `metadata/*_schema.toml`, `ingest.py` |
| Regels worden **afgekapt of aangevuld** tot het schema; gevulde velden voorbij het schema zijn een melding | DUO vult regels op met lege velden, dus korte regels zijn normaal. Een extra gevuld veld wijst op een verschoven bestand | Korte regels weigeren | Extra gevulde velden en onbekende recordsoorten geven de *error* `Inlezen`, zonder de rest te blokkeren | `ingest.read_multi_record_csv` |
| **Alleen de huidige BLB-versie**, niet de oude (`_OUD`, tot september 2019) | De oude versie heeft een andere veldlijst en is door het opvullen niet aan het aantal velden te herkennen | Beide versies ondersteunen met een bestandsnaam-schakelaar | Een `_OUD`-bestand wordt niet herkend en overgeslagen. **[Te checken]** of oude bestanden nog gebruikt worden | `analyse_schema.toml` |
| **Ongeldige datum wordt `null`**, de ruwe tekst blijft in `<veld>_Ruw` | Een datum die niet te lezen is mag niet stil verdwijnen, maar ook de run niet breken | De hele levering weigeren | Het verlies is terug te vinden in de brondata | `decode._decode_datums` |
| **`-1` in BLB wordt `null`** met een vlag `<veld>_NVT` | `-1` betekent *niet van toepassing*; als getal zou het gemiddelden en sommen vervuilen | `-1` laten staan; `0` invullen | Een teller is `null` én je ziet dat het *n.v.t.* was in plaats van *onbekend* | `decode._decode_nvt` |
| **`CodeBekostigingstatus` blijft tekst** (`na,ti`), genormaliseerd naar kleine letters en oplopend gesorteerd | Zo werkt CSV-export en blijft het veld één-op-één met de bron. Het star schema splitst de codes in een brugtabel | Een lijstkolom | Voor tellen per code is `fact_status` nodig | `decode._normaliseer_status`, `star._fact_status` |
| De **bestandsnaam** wordt tolerant gelezen: hoofdletterongevoelig, en een spatie na de eerste underscore mag (zoals het PvE noteert) | Het PvE zelf schrijft `TTTTTT_ 1234`; echte bestanden verschillen | Strikt het patroon eisen | Alles wat daarna niet past, zoals `… (1).csv`, wordt niet herkend en door de app gemeld | `ingest.parse_bestandsnaam` |
| De **BRIN en het jaar in de bestandsnaam** worden tegen het VLP gecontroleerd; de BRIN is een *error*, het jaar een *warning* | Een andere BRIN betekent de verkeerde instelling; bij een afwijkend jaar is het VLP leidend | Alleen het VLP gebruiken | Zie [Kwaliteit](kwaliteit.md) | `validate._bestandsnaam` |
| Een onbekende **codelijstwaarde** is een *warning*, geen *error* | DUO kan codes toevoegen. `dim_status` vangt onbekende statuscodes op | Weigeren | De data blijft bruikbaar; de melding wijst de code aan | `validate._codelijsten` |
| **HISBEK heeft een eigen codelijst voor inschrijvingsvorm** (`A`, `E`, `S`, `T`); BRD houdt `E` en `S` | Het PvE kent in HRD ook auditors en toegelaten studenten (§19.7.2), in BRD niet | Eén gedeelde lijst met A/T: verzwakt de controle op VLPBEK en DEFBEK | Een echt HISBEK-bestand geeft geen onterechte codelijstmeldingen | `inschrijvingsvorm_hisbek.csv` |
| `required_fields` volgt **"Verplicht = ja" uit het PvE**, behalve voor de BLB-tellers die `-1` kunnen zijn | Een lege verplichte waarde is een fout in de bron | Alles controleren | Zie [Recordtypes](recordtypes/index.md). Een uitgeschreven PvE-lijst in de tests bewaakt de HRD- en HRR-velden los van het schema | `*_schema.toml`, `tests/test_pve_hisbek.py` |
| Een **error** zet de status op `fail`, maar de uitvoer wordt **altijd geschreven** | De diagnose moet te lezen blijven. Afnemers die op exitcode afgaan, zien wél het verschil | Niets schrijven bij een fout | `--allow-quality-errors` is de override. Zie [Kwaliteit](kwaliteit.md) | `kwaliteit.poort` |
| Opnieuw verwerken **ruimt alleen eigen tabellen op** in de doelmap (recordsoorten uit de schema's, `LEVERING`, `VALIDATIE`) | Een recordsoort die in de nieuwe versie ontbreekt mag niet blijven hangen, maar een verkeerd gekozen doelmap mag ook geen bestanden van de gebruiker wissen | Alles in de map wissen; weigeren bij een niet-lege map | Een eigen bestand dat toevallig `BRD.parquet` heet, wordt wel overschreven | `pipeline._maak_leeg` |
| De **demo-sleutel** van de app geldt **alleen voor demo-data** (BRIN `99XX` in naam én VLP) | De sleutel is openbaar; een pseudoniem ermee is terug te rekenen naar het BSN | Alleen waarschuwen | Echte data verwerken in de app vraagt `EENCIJFERHO_ENCRYPT_KEY` (fail-closed) | `demo.is_demo_bestand`, `app/_utils.pseudonimiseringssleutel` |
| Een **dubbel bestand** (zelfde naam) wordt één keer geteld | Anders zouden de cijfers dubbel tellen na een dubbele download | Beide verwerken | Een *warning* `Dubbel`; het eerste bestand telt | `pipeline.verwerk_alles` |

## Analysemodel

| Keuze | Waarom | Alternatief | Gevolg | Code |
|---|---|---|---|---|
| **Natuurlijke sleutels**: `levering`, `_persoon_id`, `BRIN`, `Opleidingscode`, `Code` | Gelijk aan mbo-bekostiging-bestanden; leesbaar en stabiel | Surrogaatsleutels | Een sleutel is te herkennen zonder opzoeken | `star.py` |
| **Alle leveringen blijven naast elkaar bestaan** (geen ontdubbeling over leveringen heen); de `levering`-kolom onderscheidt ze | Voorlopig en definitief naast elkaar leggen is precies wat je wilt zien. MBO kent een canonicalisatie die een inschrijving tot één levering terugbrengt; hier zou dat de vergelijking onmogelijk maken | Alleen de nieuwste levering per deelname bewaren | Tellen over alle leveringen telt een deelname dubbel; kies in je analyse één `levering` of de nieuwste per jaar en soort (zoals het dashboard doet) | `star._feiten`, `indicatoren.actuele_leveringen` |
| **`_persoon_id` = BSN, anders onderwijsnummer** | Een student zonder BSN heeft alleen een onderwijsnummer en moet toch te volgen zijn | Alleen het BSN | Iemand met beide gebruikt het BSN; een onderwijsnummer koppelt alleen aan bestanden die hetzelfde onderwijsnummer hebben | `star._persoon_id` |
| **`dim_persoon` en `dim_opleiding` nemen per veld de eerste niet-lege waarde, nieuwste levering eerst** | Kenmerken kunnen per levering verschillen of leeg zijn; de nieuwste is het meest actueel | Eerste levering; een rij per levering | Eén rij per persoon of opleiding, met samengevoegde gegevens | `star._nieuwste_eerst` |
| **`EigenInstelling` = BRIN van de ontvanger** van een bestand | De bestanden bevatten ook deelnames bij andere instellingen; het dashboard moet de eigen instelling kunnen afbakenen | Een BRIN instellen in de configuratie | Meerdere ontvangers zijn mogelijk; alle krijgen `true` | `star._dim_instelling` |
| **`_feit_id` = `D:`/`R:` + levering + rijnummer binnen de levering** | `Inschrijvingvolgnummer` is in HRD niet verplicht, dus er is geen natuurlijke feitsleutel. Een brugtabel moet toch kunnen verwijzen | Een globaal rijnummer | Stabiel als er een levering bijkomt; niet stabiel als de rijvolgorde in een bronbestand verandert | `star._feiten` |
| **Statuscodes in een brugtabel** (`fact_status`) | Eén deelname kan meerdere codes hebben (`na,ti`); tellen per reden kan alleen met één rij per code | Een lijstkolom | Een deelname telt bij elke code mee | `star._fact_status` |
| **Onbekende statuscodes** komen in `dim_status` als *Onbekende code (niet in de PvE)* | Een code die DUO toevoegt mag geen join breken | Weigeren; weglaten | De koppeling blijft heel; de code is zichtbaar | `star._dim_status` |
| **Statusgroepen zijn een eigen indeling** (*Verbruik en limieten*, *Aanlevering*, …) | De PvE geeft geen groepen. Ze maken redenen in het dashboard leesbaar | Alleen losse codes | **[Te checken]**; de groepen zijn niet van DUO | `bekostigingstatus.csv` |
| **"Beoordeeld" = zonder status `mv`** | PvE §17.5: deelnames met `mv` vallen buiten de beoordeling en worden alleen opgenomen voor het complete beeld | Alles in het bestand als beoordeeld tellen | **[Te checken]**; de trechter, redenen, per-opleiding en historie gebruiken dit | `indicatoren.BUITEN_BEOORDELING` |
| **Voorlopig tegenover definitief** koppelt op jaar, BRIN, inschrijvingvolgnummer en persoon | Zo is een deelname in beide leveringen dezelfde | Op `_feit_id`: dat verschilt per levering | Alleen jaren met zowel VLPBEK als DEFBEK; een deelname zonder tegenhanger valt weg | `indicatoren.voorlopig_vs_definitief` |
| Het **bekostigingsjaar** van een feitrij komt uit het record zelf (HRD, HRR), anders uit de levering (BRD, BRR) | BRD en BRR hebben geen eigen jaar | Het jaar uit de bestandsnaam | Bij HISBEK is het jaar in de bestandsnaam alleen het laatste jaar | `star._feiten` |
| **Tabellen zonder bron zijn leeg met vaste kolommen** | Een instelling zonder HISBEK moet dezelfde queries kunnen draaien | De tabel weglaten | Een lege `fact_loopbaan` is geen fout | `star._met_template` |
| **Persoonsgegevens verlaten de dimensie niet**: BSN en onderwijsnummer staan alleen in `dim_persoon`, de feiten dragen `_persoon_id` | Eén plek om te beschermen of weg te laten | Persoonsgegevens in elke feittabel | Koppelen gaat via `_persoon_id` | `star._feiten` |
| Het star schema **weigert een mix** van gepseudonimiseerde en niet-gepseudonimiseerde leveringen | Een pseudoniem en een leesbaar BSN van dezelfde student koppelen niet; stil mengen zou studenten dubbel tellen | Doorgaan met een waarschuwing | Alle leveringen moeten met dezelfde keuze zijn verwerkt | `star._controleer_pseudonimisering` |
| **Contracten op het star schema** zijn declaratief (`GRAIN` en `KOPPELINGEN`) | Een nieuwe tabel voeg je toe in een register, niet in een if-keten | Controles verspreid in de bouwcode | Uniciteit, lege sleutels en koppelingen zijn *errors* | `contracten.py` |
| **Gedeeld kwaliteitscontract met MBO**: dezelfde namen voor ernst, status, `quality.json` en exitcodes | Een gedeelde kernbibliotheek (zie de roadmap) wordt zo eenvoudiger | Een eigen vorm | Een afnemer kan beide repo's met dezelfde logica lezen, voor zover de namen gelijk zijn gebleven | `kwaliteit.py` |

## Wat de tool bewust niet doet

- **De bekostiging niet opnieuw uitrekenen.** De tool maakt de uitkomst van DUO toegankelijk.
- **Opleidings- en instellingsnamen toevoegen.** Die staan niet in de DUO-bestanden. Een
  koppeling met RIO (`cedanl/rio-onderwijsdata`) staat op de roadmap.
- **De overige HO-bestanden** (OBO, verschillenlijst, registratieoverzicht, landelijk
  overzicht) inlezen. Zie de [roadmap](https://github.com/cedanl/ho-bekostiging-bestanden#roadmap).
- **Validatie op veldlengte of formaat** (AN4, N2, …). Alleen typen, verplichte velden en
  codelijsten worden gecontroleerd.
