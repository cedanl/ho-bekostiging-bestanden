"""CLI voor de HO-bekostigingsbestanden pipeline.

Gebruik:
    ho verwerk <source> <target> [--fmt parquet|csv]
"""

import argparse
from pathlib import Path

from ho_bekostiging_bestanden.pipeline import run_pipeline


def _verwerk(args: argparse.Namespace) -> None:
    frames = run_pipeline(args.source, args.target, fmt=args.fmt)
    total = sum(df.height for df in frames.values())
    print(f"Verwerkt: {len(frames)} tabellen, {total} rijen → {args.target}")


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

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)
