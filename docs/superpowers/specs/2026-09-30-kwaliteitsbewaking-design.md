# Kwaliteitsbewaking op MBO-niveau — ontwerp

Datum: 30-09-2026 · Branch: `feat/kwaliteitsbewaking` · Pitch: #18 (T1 #19, T2 #20, T3 #21, T4 #22)

## Doel

HO verwerkt nu alles stil door: `valideer()` blokkeert niets, onbekende
recordsoorten en te veel velden worden alleen gemeld, en het star schema wordt
niet gecontroleerd. Een analist moet op de uitvoer kunnen vertrouwen, of een
harde stop krijgen met een duidelijke reden.

`mbo-bekostiging-bestanden` heeft dit sinds v3.2–v3.3 opgelost. We nemen het
**contract** over (ernst, status, poort, exitcodes, `quality.json`), niet de
MBO-specifieke implementatie. Namen zijn gelijk aan MBO, zodat de gedeelde
kernbibliotheek (#9) later eenvoudig is.

**Klaar als:** elke task een eigen commit met tests heeft, de demo de status `ok`
krijgt en de suite op Linux en Windows groen is.

## Buiten scope (No-Gos)

- MBO-specifieke onderdelen: TBGI/XML, koppelregels RO↔GRONDSLAG, tijdsgebonden
  geldigheid, canonicalisatie van overlappende leveringen, SLR-tri-state.
- Referentiedata-manifest met sha256 van de codelijsten (MBO #132).
- Waardedomeincontrole per veld buiten de codelijsten (MBO #205).
- Git-commit in de provenance: het pakket draait ook buiten een git-checkout.
- Het pseudonimiseringsalgoritme blijft onaangeroerd (koppeling met 1CHO).

## Gedeeld contract (`kwaliteit.py`, nieuw)

Eén kleine module zonder afhankelijkheden op `star`/`pipeline`:

| Naam | Betekenis |
|---|---|
| `ERNST_ERROR = "error"`, `ERNST_WARNING = "warning"` | Ernst van een melding |
| `STATUS_OK = "ok"`, `STATUS_WARN = "warn"`, `STATUS_FAIL = "fail"` | Status |
| `status(meldingen: pl.DataFrame) -> str` | `fail` bij ≥1 error, `warn` bij alleen warnings, anders `ok` |
| `class KwaliteitsFout(Exception)` | Draagt `meldingen: pl.DataFrame` (de error-meldingen, in `RAPPORT_SCHEMA`) |
| `poort(meldingen, verwijzing)` | Gooit `KwaliteitsFout` als de status `fail` is |
| `QUALITY_JSON = "quality.json"` | Bestandsnaam |
| `bouw_rapport(...)`, `schrijf_rapport(...)` | De inhoud van `quality.json` en het wegschrijven ervan (UTF-8) |
| `lees_status(pad) -> tuple[str, int]` | `(status, aantal errors)` uit een geschreven rapport |

Een melding heeft overal dezelfde kolommen (`MELDING_SCHEMA`):
`Controle`, `Recordsoort`, `Melding`, `Aantal`, `Ernst`. Voor star-meldingen is
`Recordsoort` de tabelnaam. Over leveringen heen komt daar de kolom `Bron` bij
(`RAPPORT_SCHEMA`): het leveringslabel, of `STAR_BRON = "star schema"`.

*Bijgesteld tijdens het plannen:* `KwaliteitsFout` draagt de meldingen en niet
de `quality.json`-dict. `run_pipeline` gooit hem ook, en die schrijft geen
`quality.json`.

## T1 — Ernst en kwaliteitspoort (#19)

**validate.py**
- `VALIDATIE_SCHEMA` wordt `MELDING_SCHEMA` (kolom `Ernst` erbij).
- De ernst per controle staat in één mapping bovenaan het bestand:

  | Controle | Ernst | Waarom |
  |---|---|---|
  | `Inlezen` (onbekende recordsoort, meer gevulde velden dan het schema) | error | Verschoven of onbekende data; de uitvoer is dan niet te vertrouwen |
  | `Aantal records` (SLR wijkt af of ontbreekt) | error | Levering onvolledig of kapot |
  | `Eén rij` | error | VLP/SLR structureel fout |
  | `Verplicht veld` | error | Sleutel- en kernvelden ontbreken |
  | `BRIN` (bestandsnaam ≠ VLP) | error | Verkeerde instelling |
  | `Bekostigingsjaar` (bestandsnaam ≠ VLP) | warning | Alleen een naamgevingsafwijking; de VLP is leidend |
  | `Codelijst` (onbekende code) | warning | Wordt in `dim_status` al als "Onbekende code" opgevangen |

  De huidige controle `Bestandsnaam` wordt daarvoor gesplitst in `BRIN` en
  `Bekostigingsjaar`.

**pipeline.py**
- `run_pipeline(..., fail_on_errors=True)`: schrijft de prepared-uitvoer
  (inclusief `VALIDATIE`) altijd weg en gooit daarna `KwaliteitsFout` als de
  status van de levering `fail` is.
- `run_star(..., fail_on_errors=True)`: leest de gestapelde `VALIDATIE` per
  levering en voegt de star-meldingen (T2) toe. Het schrijft `datamodel/` en
  `quality.json` altijd weg en gooit daarna `KwaliteitsFout` bij `fail`.
  In T1 bevat `quality.json` status, totalen en meldingen per levering en
  voor het star schema; T3 voegt provenance, dekking en het JSON Schema toe.
  Een prepared-map zonder kolom `Ernst` (van vóór deze wijziging) levert de
  error "prepared-map verouderd; verwerk opnieuw" op (fail-closed).
- `verwerk_alles(...)`: roept `run_pipeline` aan met `fail_on_errors=False`,
  zodat alle bestanden verwerkt worden. Hij gooit **geen** `KwaliteitsFout`,
  maar geeft in `Verwerking` de velden `status` en `meldingen` (`RAPPORT_SCHEMA`)
  terug. Zo raakt de app de meldingen per bestand (dubbel, geen VLP) niet
  kwijt. Het veld `validatie` vervalt; `meldingen` vervangt het.

**cli.py**
- `EXIT_KWALITEIT = 3`; exitcode 1 blijft voor invoerfouten.
- `ho verwerk` en `ho star` krijgen `--allow-quality-errors`. Met die optie
  volgt exitcode 0 en een regel `Let op: kwaliteitsstatus fail (n error(s)), toegestaan.`
- Zonder die optie vangt `main()` de `KwaliteitsFout` af en meldt hij de fout
  zonder traceback, met exitcode 3.

**app (Home)**
- Bij status `fail`: `st.error` met het aantal errors en een tabel met de
  error-meldingen (Bron, Controle, Recordsoort, Melding, Aantal); geen
  "gelukt"-melding.
- Warnings staan in een expander met het aantal in de kop.
- *Bijgesteld tijdens het plannen:* geen vinkje "Ook verwerken bij
  kwaliteitsfouten". De uitvoer wordt altijd geschreven, dus er valt niets te
  schakelen; de status en de banner (T3) maken het zichtbaar.

## T2 — Register met star-contracten (#20)

Nieuwe module `contracten.py` (MBO: `contracts.py`, #365), los van de bouw
in `star.py`.

- **Uniciteit per grain.** Eén declaratieve lijst `GRAIN`:
  `dim_levering: [levering]`, `dim_persoon: [_persoon_id]`,
  `dim_instelling: [BRIN]`, `dim_opleiding: [Opleidingscode]`,
  `dim_status: [Code]`, `fact_deelname: [_feit_id]`,
  `fact_resultaat: [_feit_id]`, `fact_status: [_feit_id, Code]`,
  `fact_loopbaan: [levering, _persoon_id]`.
- **Geen lege sleutels.** Geen null in de grain-kolommen.
- **Referentiële integriteit.** Een declaratieve lijst `KOPPELINGEN`
  (feit, kolom → dim, kolom):
  - `levering` in elke feittabel → `dim_levering`;
  - `_persoon_id` in `fact_deelname`/`fact_resultaat`/`fact_loopbaan` → `dim_persoon`;
  - `BRIN` in `fact_deelname`/`fact_resultaat` → `dim_instelling`;
  - `Opleidingscode` in `fact_deelname`/`fact_resultaat` → `dim_opleiding`;
  - `Code` in `fact_status` → `dim_status`;
  - `_feit_id` in `fact_status` → `fact_deelname` ∪ `fact_resultaat`.

  Null-waarden in een koppelkolom vallen onder "lege sleutel" en niet onder
  "wees".
- **Register.** `CONTROLES: list[Controle]` met `naam`, `ernst` en een functie
  `(star) -> list[dict]`. `controleer_star(star) -> pl.DataFrame` (in
  `MELDING_SCHEMA`) loopt het register door. Alle drie de soorten zijn `error`.
- De demo levert 0 meldingen op (nagegaan op 30-09-2026).

## T3 — `quality.json` met provenance (#21)

`run_star` schrijft `<output>/quality.json` als UTF-8 (`ensure_ascii=False`):

```json
{
  "schema_version": 1,
  "status": "ok|warn|fail",
  "fouten_toegestaan": false,
  "total_errors": 0,
  "total_warnings": 0,
  "provenance": {
    "pakketversie": "0.1.0",
    "python": "3.13.x",
    "polars": "1.x",
    "aangemaakt": "2026-09-30T12:00:00+02:00"
  },
  "leveringen": [
    {"levering": "…", "bestandsnaam": "…", "sha256": "…", "status": "ok",
     "meldingen": [ {"controle": "…", "recordsoort": "…", "melding": "…", "aantal": 1, "ernst": "warning"} ]}
  ],
  "star": {"status": "ok", "meldingen": []},
  "dekking": [ {"levering": "…", "recordsoort": "BRD", "rijen": 123} ]
}
```

- `sha256` van het ruwe bronbestand: `run_pipeline` berekent het en zet het als
  kolom `Sha256` in `LEVERING`. `dim_levering` neemt het over; oudere
  prepared-mappen krijgen null, zoals nu al gebeurt bij `Gepseudonimiseerd`.
- `dekking`: het aantal rijen per levering × recordsoort uit de gestapelde
  tabellen. Recordsoorten komen uit de schema-TOML's en staan niet als vaste
  lijst in de code.
- `metadata/quality.schema.json` (JSON Schema, strikt:
  `additionalProperties: false`). Een test valideert de demo-uitvoer ertegen;
  daarvoor komt `jsonschema` in de dev-dependencies.
- App: Dashboard en Resultaten tonen een banner als `lees_status` `fail` of
  `warn` geeft.

## T4 — Windows-robuustheid en CI (#22)

- `encoding="utf-8"` bij elke tekstuele `open`/`read_text`/`write_text` in
  `src/`, `app/`, `scripts/` en `tests/`.
- Ruff: `PLW1514` (`unspecified-encoding`) in `select`. Dit is een
  preview-regel, dus aangezet met `preview = true` en
  `explicit-preview-rules = true`.
- *Bijgesteld tijdens het plannen:* `PLW1514` ziet alleen aanroepen waarvan
  het type bekend is, en dus niet `tmp_path / "x"`. Daarom komt er ook een
  AST-guard-test (`tests/test_encoding.py`) die elke `open`/`read_text`/`write_text`
  zonder `encoding=` in `src/`, `app/`, `scripts/` en `tests/` meldt.
- CI: een matrix over `ubuntu-latest` en `windows-latest` voor `pytest`; lint,
  format en ty alleen op Ubuntu.
- CLI-uitvoer blijft ASCII (is al zo).

## Volgorde

T4 eerst: klein, en daarna bewaakt CI de rest ook op Windows. Dan T1 → T2 → T3;
T3 bouwt voort op de meldingen van T1 en T2. Alles gebeurt op
`feat/kwaliteitsbewaking`, met één commit per task en één PR die de vier
sub-issues sluit.

## Testen

TDD per task. Naast de demo-fixtures komen kleine synthetische bestanden die
precies één error of warning uitlokken: een onbekende recordsoort, een extra
veld, een SLR-mismatch, een BRIN-mismatch, een jaar-mismatch en een onbekende
statuscode. Star-contracten worden getest met een handgemaakt star-dict met
precies één dubbeling, één null en één wees. CLI-exitcodes 0, 1 en 3 worden
getest met en zonder `--allow-quality-errors`.
