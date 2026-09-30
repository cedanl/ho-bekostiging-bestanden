"""Samenvoegen van prepared leveringen (voorlopig, definitief, historisch)."""

from collections.abc import Sequence
from pathlib import Path

import polars as pl

LABEL_COL = "levering"


def stack_prepared(
    sources: Sequence[Path | str],
    label_col: str = LABEL_COL,
    labels: list[str] | None = None,
) -> dict[str, pl.DataFrame]:
    """Voeg de Parquet-tabellen van meerdere prepared-mappen samen.

    Elke map is één levering. Er komt een leveringskolom (eerste kolom) bij,
    standaard de mapnaam. Tabellen met dezelfde naam worden onder elkaar
    gezet; ontbrekende kolommen worden met ``null`` gevuld.

    Args:
        sources:   Mappen met Parquet-bestanden (één per levering).
        label_col: Naam van de leveringskolom.
        labels:    Labels per map; standaard de mapnamen.

    Returns:
        Dict van tabelnaam naar samengevoegde DataFrame.

    Raises:
        FileNotFoundError: Als een map niet bestaat.
        ValueError:        Als ``labels`` een andere lengte heeft dan ``sources``.
    """
    paths = [Path(s) for s in sources]
    if not paths:
        return {}
    if labels is not None and len(labels) != len(paths):
        raise ValueError(
            f"labels heeft {len(labels)} elementen, sources heeft {len(paths)}"
        )
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(f"Bronmap niet gevonden: {p}")

    labels = labels or [p.name for p in paths]
    tables: dict[str, list[pl.DataFrame]] = {}
    for path, label in zip(paths, labels, strict=True):
        for parquet in sorted(path.glob("*.parquet")):
            df = pl.read_parquet(parquet).with_columns(pl.lit(label).alias(label_col))
            df = df.select([label_col, *[c for c in df.columns if c != label_col]])
            tables.setdefault(parquet.stem, []).append(df)

    return {
        tabel: pl.concat(frames, how="diagonal_relaxed")
        for tabel, frames in tables.items()
    }
