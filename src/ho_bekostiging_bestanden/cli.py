"""CLI voor de HO-bekostigingsbestanden pipeline.

Gebruik:
    ho verwerk <source> <target> [--fmt parquet|csv]
    ho star <map...> --output <map>
"""

import argparse
import sys
from pathlib import Path

from ho_bekostiging_bestanden.pipeline import run_pipeline, run_star


def _verwerk(args: argparse.Namespace) -> None:
    frames = run_pipeline(args.source, args.target, fmt=args.fmt)
    total = sum(df.height for df in frames.values())
    print(f"Verwerkt: {len(frames)} tabellen, {total} rijen -> {args.target}")


def _star(args: argparse.Namespace) -> None:
    star = run_star(args.sources, args.output)
    total = sum(df.height for df in star.values())
    print(f"Star schema gebouwd: {len(star)} tabellen, {total} rijen -> {args.output}")


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
