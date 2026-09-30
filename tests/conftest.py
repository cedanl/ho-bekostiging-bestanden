"""Gedeelde testhelpers: bouw kleine, realistische DUO-bestanden in tmp-mappen.

Regels worden opgebouwd vanuit de schema-TOML's, zodat tests meebewegen met de
veldindeling. Bestanden krijgen CRLF-regeleinden en worden opgevuld tot
minstens 25 velden, zoals de echte DUO-bestanden.
"""

from pathlib import Path

import pytest

from ho_bekostiging_bestanden.demo import maak_regel, schrijf_bestand
from ho_bekostiging_bestanden.pipeline import verwerk_alles

DEMO_RAW = Path(__file__).parents[1] / "data" / "01-raw" / "demo"

__all__ = [
    "DEMO_RAW",
    "analyse_regels",
    "hisbek_regels",
    "maak_regel",
    "schrijf_bestand",
]


def _brd(bsn: str, onr: str, brin: str, volgnr: str, ind: str, code: str) -> str:
    return maak_regel(
        "analyse",
        "BRD",
        Burgerservicenummer=bsn,
        Onderwijsnummer=onr,
        BRIN=brin,
        Inschrijvingvolgnummer=volgnr,
        Bekostigingsindicatie=ind,
        CodeBekostigingstatus=code,
        Bekostigingsniveau="LAAG",
        Opleidingscode="34001",
        Opleidingsniveau="HBO-BA",
        Opleidingsfase="B",
        DatumInschrijving="20230901",
        DatumUitschrijving="20240831",
        EersteInschrijving="J",
        Inschrijvingsvorm="S",
        Onderwijsvorm="VT",
        DatumEersteAanlevering="20230915",
        Bekostigingsduur="12",
        OpleidingOnderdeel="TECHNIEK",
        Bekostigingscode="BEKOSTIGD",
        IndicatieSectorLG="N",
        IndicatieBaMa="B",
        IndicatieAcademischZiekenhuis="N",
        IndicatieNationaliteitsvoorwaardeSF="J",
        IndicatieGBARelatie="J",
    )


def analyse_regels(
    jaar: int = 2025, statussen: tuple[str, ...] | None = None
) -> list[str]:
    """Mini-analysebestand: 2 personen, 3 BRD, 1 BRR, 1 BLB.

    Persoon 1 heeft BSN en onderwijsnummer; persoon 2 alleen een
    onderwijsnummer. ``statussen`` overschrijft de drie BRD-statuscodes.
    """
    s1, s2, s3 = statussen or ("pi", "mv", "na,ti")
    ind = {c: ("J" if c in {"pi", "pd"} else "N") for c in (s1, s2, s3)}
    return [
        maak_regel(
            "analyse",
            "VLP",
            BRIN="99XX",
            Bekostigingsjaar=str(jaar),
            DatumAanmaak=f"{jaar - 1}0115",
        ),
        maak_regel(
            "analyse",
            "BLB",
            Burgerservicenummer="700010001",
            Onderwijsnummer="800010001",
            DatumGraadBehaaldBa="20230625",
            VerbruikBA="1",
            AantalBekostigdeInschrijvingenBa="1",
            AantalBekostigdeInschrijvingenMa="-1",
        ),
        _brd("700010001", "800010001", "99XX", "INS001", ind[s1], s1),
        _brd("700010001", "800010001", "71AA", "EXT001", ind[s2], s2),
        maak_regel(
            "analyse",
            "BRR",
            Burgerservicenummer="700010001",
            Onderwijsnummer="800010001",
            BRIN="99XX",
            Resultaatvolgnummer="RES001",
            Bekostigingsindicatie="J",
            CodeBekostigingstatus="pg",
            Bekostigingsniveau="LAAG",
            JointDegreeFactor="1",
            Opleidingscode="34001",
            Opleidingsniveau="HBO-BA",
            Opleidingsfase="B",
            EersteGraad="J",
            DatumDiploma="20230625",
            Onderwijsvorm="VT",
            DatumEersteAanlevering="20230701",
            OpleidingOnderdeel="TECHNIEK",
            Bekostigingscode="BEKOSTIGD",
            IndicatieSectorLG="N",
            IndicatieBaMa="B",
            IndicatieAcademischZiekenhuis="N",
            IndicatieGraadTeltVoorBekostigingsloopbaan="J",
            IndicatieNationaliteitsvoorwaardeSF="J",
            IndicatieGBARelatie="J",
        ),
        _brd("", "800010002", "99XX", "INS002", ind[s3], s3),
        maak_regel(
            "analyse",
            "SLR",
            AantalBLBrecords="1",
            AantalBRDrecords="3",
            AantalBRRrecords="1",
        ),
    ]


def hisbek_regels() -> list[str]:
    """Mini-HISBEK: 1 persoon, HRD voor 2023 en 2024, 1 HRR in 2024."""

    def hrd(jaar: str, code: str, ind: str) -> str:
        return maak_regel(
            "hisbek",
            "HRD",
            Burgerservicenummer="700010001",
            Onderwijsnummer="800010001",
            Bekostigingsjaar=jaar,
            BRIN="99XX",
            Inschrijvingvolgnummer="INS000",
            Bekostigingsindicatie=ind,
            CodeBekostigingstatus=code,
            Bekostigingsniveau="LAAG",
            Opleidingscode="34001",
            Opleidingsniveau="HBO-BA",
            Opleidingsfase="B",
            DatumInschrijving="20210901",
            DatumUitschrijving="20220831",
            EersteInschrijving="J",
            Inschrijvingsvorm="S",
            Onderwijsvorm="VT",
            DatumEersteAanlevering="20210915",
            ECTS="60.0",
            ECTSBekostigd="60.0",
            OpleidingOnderdeel="TECHNIEK",
            IndicatieNationaliteitsvoorwaardeSF="J",
            IndicatieGBARelatie="J",
        )

    return [
        maak_regel("hisbek", "VLP", BRIN="99XX", DatumAanmaak="20250301"),
        hrd("2023", "pi", "J"),
        hrd("2024", "ti", "N"),
        maak_regel(
            "hisbek",
            "HRR",
            Burgerservicenummer="700010001",
            Onderwijsnummer="800010001",
            Bekostigingsjaar="2024",
            BRIN="99XX",
            Resultaatvolgnummer="RES000",
            Bekostigingsindicatie="J",
            CodeBekostigingstatus="pg",
            JointDegreeFactor="1",
            Opleidingscode="34001",
            Opleidingsniveau="HBO-BA",
            Opleidingsfase="D",
            EersteGraad="N",
            DatumDiploma="20220625",
            Onderwijsvorm="VT",
            IndicatieGraadTeltVoorBekostigingsloopbaan="N",
            IndicatieNationaliteitsvoorwaardeSF="J",
        ),
        maak_regel("hisbek", "SLR", AantalHRDrecords="2", AantalHRRrecords="1"),
    ]


@pytest.fixture
def vlpbek_bestand(tmp_path: Path) -> Path:
    return schrijf_bestand(tmp_path, "VLPBEK_2025_20240115_99XX.csv", analyse_regels())


@pytest.fixture
def hisbek_bestand(tmp_path: Path) -> Path:
    return schrijf_bestand(tmp_path, "HISBEK_2024_20250301_99XX.csv", hisbek_regels())


@pytest.fixture(scope="session")
def demo_star(tmp_path_factory) -> dict:
    """Star schema van de demo-data (één keer per testsessie gebouwd)."""
    basis = tmp_path_factory.mktemp("demo")
    return verwerk_alles(DEMO_RAW, basis / "prep", basis / "out").star
