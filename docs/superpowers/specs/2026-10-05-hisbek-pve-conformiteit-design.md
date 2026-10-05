# HISBEK: conformiteit met de PvE — design

## Aanleiding
Het HISBEK-schema, de codelijsten en de demo-generator zijn veld voor veld
vergeleken met de PvE HO-instelling – DUO v26.3.1 (17-07-2026), bijlage 10
(§19, p. 183–192). Die PvE staat in `cedanl/mbo-bekostiging-bestanden`
(`programma-van-eisen-hoger-onderwijs.pdf`).

De veldvolgorde van VLP, HRD, HRR en SLR klopt. Er zijn drie afwijkingen:

1. **Codelijst inschrijvingsvorm.** HRD kent `A`, `E`, `S` en `T`
   (§19.7.2); BRD alleen `E` en `S` (bijlage 8). Beide gebruiken nu
   `inschrijvingsvorm.csv` met alleen E/S, dus een echte HISBEK met
   auditors of toegelaten studenten geeft onterecht codelijstmeldingen.
2. **Verplichte velden.** De PvE noemt als verplicht wat het schema niet
   controleert: HRD `DatumUitschrijving` en
   `IndicatieNationaliteitsvoorwaardeSF`, HRR `Onderwijsvorm`. HRD bevat per
   definitie alleen beoordeelde deelnames (§19.5), waarvoor de PvE zegt dat
   de nationaliteitsindicator altijd gevuld is.
3. **Demo-data onrealistisch.** ECTS en ECTSBekostigd zijn alleen gevuld voor
   OU-deelnames (de demo-instelling is geen OU). `IndicatieWoonplaatsVereiste`
   en `DuitseDeelstaat` zijn alleen gevuld van 2011 t/m 2014 (de demo-jaren
   zijn 2021–2024). HRD/HRR zijn per persoon aflopend op bekostigingsjaar
   gesorteerd (§19.5).

Bovendien zijn schema en demo circulair: de demo wordt gemaakt met het schema
waarmee hij wordt ingelezen. Een fout in het schema slaagt dan ook in de tests.

## Ontwerp
- **Eigen codelijst** `inschrijvingsvorm_hisbek.csv` (A/E/S/T), gekoppeld in
  `[HRD.codelijsten]`. BRD houdt `inschrijvingsvorm.csv` (E/S). Eén gedeelde
  lijst met A/T zou de controle op VLPBEK/DEFBEK verzwakken.
- **`required_fields`** van HRD en HRR gelijk aan de kolom "Verplicht = ja" in
  §19.7.2 en §19.7.3.
- **Onafhankelijke PvE-test:** de veldvolgorde en verplichte velden van HRD/HRR
  staan uitgeschreven in de test, overgenomen uit de PvE, los van de TOML.
  Zo breekt het niet-circulaire bewijs als iemand het schema wijzigt.
- **Demo:** jaren waarin een veld gevuld is komen uit constanten bovenaan
  `demo.py`; ECTS alleen bij een OU-instelling (de demo heeft er geen);
  HISBEK-regels per persoon aflopend op jaar.

## Buiten scope
- Demo-jaren vóór 2015 (om "gevuld vanaf"-velden leeg te testen).
- Validatie op veldlengte of formaat (AN4, N2, …).
- Een echt HISBEK-bestand blijft nodig om te bevestigen dat DUO de PvE volgt.
