"""Synthetische demo-bestanden (VLPBEK/DEFBEK/HISBEK) volgens de PvE-veldindeling.

Alle personen, nummers en opleidingscodes zijn fictief. Regels worden
opgebouwd vanuit de schema-TOML's en, net als echte DUO-bestanden, opgevuld
tot 25 velden met CRLF-regeleinden. De uitkomst is deterministisch.
"""

import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ho_bekostiging_bestanden.ingest import (
    SCHEMA_PER_LEVERING,
    SEPARATOR,
    parse_bestandsnaam,
)
from ho_bekostiging_bestanden.metadata import load_schema
from ho_bekostiging_bestanden.validate import VOORLOOP

SEED = 42
DOEL = Path("data/01-raw/demo")
PAD_TOT = 25  # aantal velden waarop DUO elke regel opvult
BRIN_EIGEN = "99XX"
BRIN_ANDER = "71AA"
AANTAL_PERSONEN = 150
ELKE_ZONDER_BSN = 12  # elke 12e persoon heeft alleen een onderwijsnummer
KANS_ANDERE_INSTELLING = 0.1
KANS_RESULTAAT = 0.3
KANS_NVT = 0.05
HISBEK_OVERSLAAN = 3  # persoon mist een HISBEK-jaar als (nr + jaar) % 3 == 0
HISBEK_GRAAD_ELKE = 5  # elke 5e persoon heeft een historische graad

VOORLOPIG = [(2025, date(2024, 1, 15)), (2026, date(2025, 1, 15))]
DEFINITIEF = [(2025, date(2024, 7, 15))]
HISBEK = (2024, date(2025, 3, 1))
HISBEK_JAREN = (2021, 2022, 2023, 2024)
# PvE §19.7.2/3: DuitseDeelstaat en IndicatieWoonplaatsVereiste zijn alleen
# gevuld van 2011 t/m 2014. ECTS en ECTSBekostigd alleen voor OU-deelnames;
# de demo-instelling is geen OU, dus die blijven leeg.
WOONPLAATS_JAREN = range(2011, 2015)

# Fictieve opleidingen: (code, niveau, fase, onderdeel, bekostigingsniveau, BaMa)
OPLEIDINGEN = [
    ("34001", "HBO-BA", "B", "TECHNIEK", "HOOG", "B"),
    ("34002", "HBO-BA", "B", "ECONOMIE", "LAAG", "B"),
    ("34003", "HBO-AD", "A", "ECONOMIE", "LAAG", "D"),
    ("34004", "HBO-MA", "M", "GEZONDHEIDSZORG", "HOOG", "M"),
    ("34005", "HBO-BA", "B", "ONDERWIJS", "LAAG", "B"),
    ("34006", "HBO-BA", "B", "TAAL_EN_CULTUUR", "LAAG", "B"),
    ("56001", "WO-BA", "B", "RECHT", "LAAG", "B"),
    ("56002", "WO-MA", "M", "GEDRAG_EN_MAATSCHAPPIJ", "LAAG", "M"),
]
DEELNAME_STATUS = {
    "pi": 70,
    "mv": 8,
    "jl": 5,
    "ti": 4,
    "ng": 3,
    "nf": 2,
    "na": 2,
    "nr": 2,
    "pd": 2,
    "ex": 1,
    "na,ti": 1,
}
RESULTAAT_STATUS = {"pg": 60, "np": 15, "mu": 8, "mt": 7, "tg": 5, "nb": 5}
BEKOSTIGD = {"pi", "pd", "pg"}
# Kans dat een voorlopige status in de definitieve levering "pi" wordt.
DEF_HERSTEL = {"ti": 0.6, "nr": 0.5, "na,ti": 0.5}
ONDERWIJSVORM = {"VT": 75, "DT": 15, "DU": 10}
PROPEDEUSE_FASE = "D"


@dataclass(frozen=True)
class _Persoon:
    nr: int
    bsn: str
    onr: str
    opleiding: tuple[str, str, str, str, str, str]
    brins: tuple[str, ...]
    onderwijsvorm: str


def maak_regel(schema_naam: str, rs: str, **waarden: str) -> str:
    """Bouw één ``|``-regel volgens het schema; niet opgegeven velden blijven leeg.

    Raises:
        KeyError: Als een veld niet in het schema van ``rs`` staat.
    """
    velden = load_schema(schema_naam)[rs]["fields"]
    onbekend = set(waarden) - set(velden)
    if onbekend:
        raise KeyError(f"Onbekende velden voor {rs}: {sorted(onbekend)}")
    return SEPARATOR.join(
        rs if veld == "Recordsoort" else waarden.get(veld, "") for veld in velden
    )


def schrijf_bestand(map_: Path, naam: str, regels: list[str]) -> Path:
    """Schrijf regels met CRLF, opgevuld tot minstens ``PAD_TOT`` velden."""
    map_.mkdir(parents=True, exist_ok=True)
    opgevuld = [
        r + SEPARATOR * max(PAD_TOT - 1 - r.count(SEPARATOR), 0) for r in regels
    ]
    pad = map_ / naam
    pad.write_bytes(("\r\n".join(opgevuld) + "\r\n").encode("utf-8"))
    return pad


def _kies(rng: random.Random, gewichten: dict[str, int]) -> str:
    return rng.choices(list(gewichten), weights=list(gewichten.values()))[0]


def _jn(waar: bool) -> str:
    return "J" if waar else "N"


def _d(dag: date) -> str:
    return dag.strftime("%Y%m%d")


def _personen(rng: random.Random) -> list[_Persoon]:
    personen = []
    for nr in range(1, AANTAL_PERSONEN + 1):
        extra = rng.random() < KANS_ANDERE_INSTELLING
        personen.append(
            _Persoon(
                nr=nr,
                bsn="" if nr % ELKE_ZONDER_BSN == 0 else f"7000{nr:05d}",
                onr=f"8000{nr:05d}",
                opleiding=rng.choice(OPLEIDINGEN),
                brins=(BRIN_EIGEN, BRIN_ANDER) if extra else (BRIN_EIGEN,),
                onderwijsvorm=_kies(rng, ONDERWIJSVORM),
            )
        )
    # Zoals DUO: oplopend op BSN, personen met alleen een onderwijsnummer achteraan.
    return sorted(personen, key=lambda p: (p.bsn == "", p.bsn, p.onr))


def _deelname(p: _Persoon, brin: str, jaar: int, status: str) -> dict[str, str]:
    code, niveau, fase, onderdeel, bniveau, bama = p.opleiding
    codes = set(status.split(","))
    start = date(jaar - 3, 9, 1) if "mv" in codes else date(jaar - 2, 9, 1)
    aanlevering = date(jaar - 1, 3, 1) if "ti" in codes else date(start.year, 9, 15)
    return {
        "Burgerservicenummer": p.bsn,
        "Onderwijsnummer": p.onr,
        "BRIN": brin,
        "Inschrijvingvolgnummer": f"{brin}{p.nr:05d}{start.year}",
        "Bekostigingsindicatie": _jn(status in BEKOSTIGD),
        "CodeBekostigingstatus": status,
        "Bekostigingsniveau": bniveau,
        "Opleidingscode": code,
        "Opleidingsniveau": niveau,
        "Opleidingsfase": fase,
        "DatumInschrijving": _d(start),
        "DatumUitschrijving": _d(date(start.year + 1, 8, 31)),
        "EersteInschrijving": _jn("jl" not in codes),
        "Inschrijvingsvorm": "E" if "ex" in codes else "S",
        "Onderwijsvorm": p.onderwijsvorm,
        "DatumEersteAanlevering": _d(aanlevering),
        "Bekostigingsduur": "12",
        "OpleidingOnderdeel": onderdeel,
        "Bekostigingscode": "BEKOSTIGD",
        "IndicatieSectorLG": "N",
        "IndicatieBaMa": bama,
        "IndicatieAcademischZiekenhuis": "N",
        "IndicatieNationaliteitsvoorwaardeSF": _jn("nr" not in codes),
        "IndicatieGBARelatie": _jn("na" not in codes),
    }


def _resultaat(p: _Persoon, jaar: int, status: str) -> dict[str, str]:
    code, niveau, fase, onderdeel, bniveau, bama = p.opleiding
    diploma = {"mt": date(jaar - 2, 11, 1), "mu": date(jaar - 3, 6, 25)}.get(
        status, date(jaar - 2, 6, 25)
    )
    aanlevering = (
        date(diploma.year, 12, 1) if status == "tg" else date(diploma.year, 7, 15)
    )
    return {
        "Burgerservicenummer": p.bsn,
        "Onderwijsnummer": p.onr,
        "BRIN": BRIN_EIGEN,
        "Resultaatvolgnummer": f"R{p.nr:05d}{diploma.year}",
        "Bekostigingsindicatie": _jn(status in BEKOSTIGD),
        "CodeBekostigingstatus": status,
        "Bekostigingsniveau": bniveau,
        "JointDegreeFactor": "1",
        "Opleidingscode": code,
        "Opleidingsniveau": niveau,
        "Opleidingsfase": PROPEDEUSE_FASE if status == "np" else fase,
        "EersteGraad": _jn(status != "np"),
        "DatumDiploma": _d(diploma),
        "Onderwijsvorm": p.onderwijsvorm,
        "DatumEersteAanlevering": _d(aanlevering),
        "OpleidingOnderdeel": onderdeel,
        "Bekostigingscode": "BEKOSTIGD",
        "IndicatieSectorLG": "N",
        "IndicatieBaMa": bama,
        "IndicatieAcademischZiekenhuis": "N",
        "IndicatieGraadTeltVoorBekostigingsloopbaan": _jn(status != "np"),
        "IndicatieNationaliteitsvoorwaardeSF": "J",
        "IndicatieGBARelatie": "J",
    }


def _loopbaan(p: _Persoon, jaar: int, graad: date | None) -> dict[str, str]:
    rng = random.Random(f"{SEED}-{p.nr}-{jaar}")
    waarden = {"Burgerservicenummer": p.bsn, "Onderwijsnummer": p.onr}
    if graad is not None:
        waarden["DatumGraadBehaaldBa"] = _d(graad)
    for veld in load_schema("analyse")["BLB"]["int_fields"]:
        waarden[veld] = "-1" if rng.random() < KANS_NVT else str(rng.randint(0, 3))
    return waarden


def _trek_statussen(
    rng: random.Random, personen: list[_Persoon]
) -> tuple[dict[tuple[int, str], str], dict[int, str]]:
    deelnames = {
        (p.nr, brin): _kies(rng, DEELNAME_STATUS) for p in personen for brin in p.brins
    }
    resultaten = {
        p.nr: _kies(rng, RESULTAAT_STATUS)
        for p in personen
        if rng.random() < KANS_RESULTAAT
    }
    return deelnames, resultaten


def _herstel(
    rng: random.Random, deelnames: dict[tuple[int, str], str]
) -> dict[tuple[int, str], str]:
    return {
        sleutel: "pi" if rng.random() < DEF_HERSTEL.get(status, 0) else status
        for sleutel, status in deelnames.items()
    }


def _analysebestand(
    personen: list[_Persoon],
    jaar: int,
    aanmaak: date,
    deelnames: dict[tuple[int, str], str],
    resultaten: dict[int, str],
) -> list[str]:
    regels = [
        maak_regel(
            "analyse",
            VOORLOOP,
            BRIN=BRIN_EIGEN,
            Bekostigingsjaar=str(jaar),
            DatumAanmaak=_d(aanmaak),
        )
    ]
    tel = {"BLB": 0, "BRD": 0, "BRR": 0}
    for p in personen:
        status_r = resultaten.get(p.nr)
        graad = date(jaar - 2, 6, 25) if status_r == "pg" else None
        regels.append(maak_regel("analyse", "BLB", **_loopbaan(p, jaar, graad)))
        tel["BLB"] += 1
        for brin in p.brins:
            regels.append(
                maak_regel(
                    "analyse",
                    "BRD",
                    **_deelname(p, brin, jaar, deelnames[(p.nr, brin)]),
                )
            )
            tel["BRD"] += 1
        if status_r is not None:
            regels.append(maak_regel("analyse", "BRR", **_resultaat(p, jaar, status_r)))
            tel["BRR"] += 1
    regels.append(
        maak_regel(
            "analyse", "SLR", **{f"Aantal{rs}records": str(n) for rs, n in tel.items()}
        )
    )
    return regels


def _woonplaatsvereiste(jaar: int, voldoet: bool) -> str:
    return _jn(voldoet) if jaar in WOONPLAATS_JAREN else ""


def _hisbek(rng: random.Random, personen: list[_Persoon], aanmaak: date) -> list[str]:
    regels = [maak_regel("hisbek", VOORLOOP, BRIN=BRIN_EIGEN, DatumAanmaak=_d(aanmaak))]
    tel = {"HRD": 0, "HRR": 0}
    for p in personen:
        # (jaar, volgorde binnen het jaar, regel); de PvE sorteert per persoon
        # aflopend op bekostigingsjaar (§19.5).
        records: list[tuple[int, int, str]] = []
        for jaar in HISBEK_JAREN:
            if (p.nr + jaar) % HISBEK_OVERSLAAN == 0:
                continue
            status = _kies(rng, DEELNAME_STATUS)
            codes = set(status.split(","))
            waarden = _deelname(p, BRIN_EIGEN, jaar, status) | {
                "Bekostigingsjaar": str(jaar),
                "IndicatieWoonplaatsVereiste": _woonplaatsvereiste(
                    jaar, "na" not in codes
                ),
            }
            records.append((jaar, 0, maak_regel("hisbek", "HRD", **waarden)))
            tel["HRD"] += 1
        if p.nr % HISBEK_GRAAD_ELKE == 0:
            jaar = HISBEK_JAREN[-1]
            waarden = _resultaat(p, jaar, "pg") | {
                "Bekostigingsjaar": str(jaar),
                "IndicatieWoonplaatsVereiste": _woonplaatsvereiste(jaar, True),
            }
            records.append((jaar, 1, maak_regel("hisbek", "HRR", **waarden)))
            tel["HRR"] += 1
        records.sort(key=lambda r: (-r[0], r[1]))
        regels += [regel for _, _, regel in records]
    regels.append(
        maak_regel(
            "hisbek", "SLR", **{f"Aantal{rs}records": str(n) for rs, n in tel.items()}
        )
    )
    return regels


def _naam(soort: str, jaar: int, aanmaak: date) -> str:
    return f"{soort}_{jaar}_{_d(aanmaak)}_{BRIN_EIGEN}.csv"


def _vlp_brin(pad: Path, schema_naam: str) -> str | None:
    """BRIN uit het voorlooprecord; alleen de eerste regel wordt gelezen."""
    with pad.open(encoding="utf-8-sig", errors="replace") as f:
        velden = f.readline().rstrip("\r\n").split(SEPARATOR)
    vlp = load_schema(schema_naam)[VOORLOOP]["fields"]
    if velden[0] != VOORLOOP or len(velden) <= vlp.index("BRIN"):
        return None
    return velden[vlp.index("BRIN")]


def is_demo_bestand(pad: str | Path) -> bool:
    """Is dit een synthetisch demo-bestand (BRIN ``BRIN_EIGEN`` in naam én VLP)?

    De app pseudonimiseert alleen demo-data met de openbare demo-sleutel. De
    VLP wordt ook gelezen, zodat een omgedoopt echt bestand niet doorglipt.
    """
    pad = Path(pad)
    info = parse_bestandsnaam(pad)
    if info is None or info.brin != BRIN_EIGEN:
        return False
    return _vlp_brin(pad, SCHEMA_PER_LEVERING[info.soort]) == BRIN_EIGEN


def genereer_demo(doel: Path = DOEL) -> list[Path]:
    """Schrijf de vier demo-bestanden naar ``doel`` en geef de paden terug."""
    personen = _personen(random.Random(SEED))
    trekkingen = {
        jaar: _trek_statussen(random.Random(f"{SEED}-{jaar}"), personen)
        for jaar, _ in VOORLOPIG
    }
    paden = []
    for jaar, aanmaak in VOORLOPIG:
        deelnames, resultaten = trekkingen[jaar]
        regels = _analysebestand(personen, jaar, aanmaak, deelnames, resultaten)
        paden.append(schrijf_bestand(doel, _naam("VLPBEK", jaar, aanmaak), regels))
    for jaar, aanmaak in DEFINITIEF:
        deelnames, resultaten = trekkingen[jaar]
        hersteld = _herstel(random.Random(f"{SEED}-def-{jaar}"), deelnames)
        regels = _analysebestand(personen, jaar, aanmaak, hersteld, resultaten)
        paden.append(schrijf_bestand(doel, _naam("DEFBEK", jaar, aanmaak), regels))
    jaar, aanmaak = HISBEK
    regels = _hisbek(random.Random(f"{SEED}-his"), personen, aanmaak)
    paden.append(schrijf_bestand(doel, _naam("HISBEK", jaar, aanmaak), regels))
    return paden
