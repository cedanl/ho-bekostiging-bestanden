"""CLI voor de HO-bekostigingsbestanden pipeline.

Gebruik:
    ho verwerk <source> <target> [--fmt parquet|csv] [--sleutelbestand <pad>]
               [--geen-pseudonimisering] [--allow-quality-errors]
    ho star <map...> --output <map> [--allow-quality-errors]

Exitcode 1 bij een invoerfout, 3 bij kwaliteitsstatus fail. De uitvoer wordt
ook bij fail geschreven; --allow-quality-errors geeft dan exitcode 0.
"""

import argparse
import sys
from pathlib import Path

from ho_bekostiging_bestanden.ingest import VALIDATIE
from ho_bekostiging_bestanden.kwaliteit import (
    ERNST_ERROR,
    QUALITY_JSON,
    STATUS_FAIL,
    KwaliteitsFout,
    aantal,
    lees_status,
    status,
)
from ho_bekostiging_bestanden.pipeline import run_pipeline, run_star
from ho_bekostiging_bestanden.pseudonimisering import SLEUTEL_ENV, laad_sleutel

# Exitcode bij kwaliteitsstatus fail, gelijk aan mbo-bekostiging-bestanden (#361).
EXIT_KWALITEIT = 3


def _meld_toegestaan(stat: str, fouten: int) -> None:
    if stat == STATUS_FAIL:
        print(f"Let op: kwaliteitsstatus {stat} ({fouten} error(s)), toegestaan.")


def _verwerk(args: argparse.Namespace) -> None:
    pseudonimiseer = not args.geen_pseudonimisering
    sleutel = (
        laad_sleutel(sleutelbestand=args.sleutelbestand) if pseudonimiseer else None
    )
    if not pseudonimiseer:
        # Vóór de verwerking: de uitvoer staat ook op schijf als de poort sluit.
        print(
            "Let op: BSN en onderwijsnummer zijn NIET gepseudonimiseerd.",
            file=sys.stderr,
        )
    frames = run_pipeline(
        args.source,
        args.target,
        fmt=args.fmt,
        sleutel=sleutel,
        pseudonimiseer=pseudonimiseer,
        fail_on_errors=not args.allow_quality_errors,
    )
    total = sum(df.height for df in frames.values())
    print(f"Verwerkt: {len(frames)} tabellen, {total} rijen -> {args.target}")
    validatie = frames[VALIDATIE]
    _meld_toegestaan(status(validatie), aantal(validatie, ERNST_ERROR))


def _star(args: argparse.Namespace) -> None:
    star = run_star(
        args.sources, args.output, fail_on_errors=not args.allow_quality_errors
    )
    total = sum(df.height for df in star.values())
    print(f"Star schema gebouwd: {len(star)} tabellen, {total} rijen -> {args.output}")
    _meld_toegestaan(*lees_status(args.output / QUALITY_JSON))


def _voeg_kwaliteitsoptie_toe(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-quality-errors",
        action="store_true",
        dest="allow_quality_errors",
        help="Exitcode 0 ook bij kwaliteitsstatus fail (uitvoer staat er altijd)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ho",
        description="HO-bekostigingsbestanden pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_verwerk = sub.add_parser("verwerk", help="Verwerk één ruw bestand")
    p_verwerk.add_argument("source", type=Path, help="Pad naar het ruwe bronbestand")
    p_verwerk.add_argument("target", type=Path, help="Doelmap voor de uitvoer")
    p_verwerk.add_argument(
        "--fmt",
        default="parquet",
        choices=["parquet", "csv"],
        help="Uitvoerformaat (standaard: parquet)",
    )
    p_verwerk.add_argument(
        "--sleutelbestand",
        type=Path,
        default=None,
        help=f"Bestand met de pseudonimiseringssleutel (standaard: ${SLEUTEL_ENV})",
    )
    p_verwerk.add_argument(
        "--geen-pseudonimisering",
        action="store_true",
        dest="geen_pseudonimisering",
        help="BSN en onderwijsnummer leesbaar laten (standaard: pseudonimiseren)",
    )
    _voeg_kwaliteitsoptie_toe(p_verwerk)
    p_verwerk.set_defaults(func=_verwerk)

    p_star = sub.add_parser("star", help="Bouw star schema vanuit prepared-mappen")
    p_star.add_argument(
        "sources",
        nargs="+",
        type=Path,
        help="Mappen met Parquet-bestanden (één per levering)",
    )
    p_star.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Doelmap; het star schema komt in <output>/datamodel/",
    )
    _voeg_kwaliteitsoptie_toe(p_star)
    p_star.set_defaults(func=_star)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (ValueError, FileNotFoundError) as fout:
        # Verwachte gebruikersfouten: nette melding, geen traceback.
        print(f"Fout: {fout}", file=sys.stderr)
        sys.exit(1)
    except KwaliteitsFout as fout:
        print(f"Fout: {fout}", file=sys.stderr)
        sys.exit(EXIT_KWALITEIT)
