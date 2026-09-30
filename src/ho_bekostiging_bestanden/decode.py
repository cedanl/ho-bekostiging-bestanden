"""Decoderen: tekstvelden omzetten naar de juiste typen via de schema-TOML."""

import polars as pl

from ho_bekostiging_bestanden.metadata import load_schema

DATUM_FORMAAT = "%Y%m%d"
WAAR = "J"
ONWAAR = "N"
NVT_WAARDE = "-1"
STATUS_VELD = "CodeBekostigingstatus"
STATUS_SCHEIDING = ","
RUW_SUFFIX = "_Ruw"
NVT_SUFFIX = "_NVT"


def _normaliseer_status(kolom: str) -> pl.Expr:
    """Kleine letters, geen spaties, codes gesorteerd: ``" TI, na"`` → ``"na,ti"``."""
    return (
        pl.col(kolom)
        .str.to_lowercase()
        .str.replace_all(r"\s", "")
        .str.split(STATUS_SCHEIDING)
        .list.eval(pl.element().filter(pl.element() != ""))
        .list.sort()
        .list.join(STATUS_SCHEIDING)
        .replace("", None)
        .alias(kolom)
    )


def _leeg_naar_null(df: pl.DataFrame) -> pl.DataFrame:
    tekst = [c for c, t in df.schema.items() if t == pl.Utf8]
    return df.with_columns(
        pl.col(c).str.strip_chars().replace("", None).alias(c) for c in tekst
    )


def _decode_datums(df: pl.DataFrame, velden: list[str]) -> pl.DataFrame:
    for veld in velden:
        geparsed = pl.col(veld).str.to_date(DATUM_FORMAAT, strict=False)
        ongeldig = pl.col(veld).is_not_null() & geparsed.is_null()
        if df.select(ongeldig.any()).item():
            df = df.with_columns(
                pl.when(ongeldig).then(pl.col(veld)).alias(f"{veld}{RUW_SUFFIX}")
            )
        df = df.with_columns(geparsed.alias(veld))
    return df


def _decode_booleans(df: pl.DataFrame, velden: list[str]) -> pl.DataFrame:
    return df.with_columns(
        pl.when(pl.col(v) == WAAR)
        .then(True)
        .when(pl.col(v) == ONWAAR)
        .then(False)
        .otherwise(None)
        .cast(pl.Boolean)
        .alias(v)
        for v in velden
    )


def _decode_nvt(df: pl.DataFrame, velden: list[str]) -> pl.DataFrame:
    return df.with_columns(
        *[
            (pl.col(v) == NVT_WAARDE).fill_null(False).alias(f"{v}{NVT_SUFFIX}")
            for v in velden
        ],
        *[pl.col(v).replace(NVT_WAARDE, None).alias(v) for v in velden],
    )


def _decode_getallen(
    df: pl.DataFrame, int_velden: list[str], float_velden: list[str]
) -> pl.DataFrame:
    return df.with_columns(
        *[pl.col(v).cast(pl.Int64, strict=False).alias(v) for v in int_velden],
        *[
            pl.col(v).str.replace(",", ".").cast(pl.Float64, strict=False).alias(v)
            for v in float_velden
        ],
    )


def _decode_recordsoort(df: pl.DataFrame, spec: dict) -> pl.DataFrame:
    df = _leeg_naar_null(df)
    if STATUS_VELD in df.columns:
        df = df.with_columns(_normaliseer_status(STATUS_VELD))
    df = _decode_datums(df, spec.get("date_fields", []))
    df = _decode_booleans(df, spec.get("bool_fields", []))
    df = _decode_nvt(df, spec.get("nvt_fields", []))
    return _decode_getallen(
        df, spec.get("int_fields", []), spec.get("float_fields", [])
    )


def decode_frames(
    frames: dict[str, pl.DataFrame],
    schema_name: str,
) -> dict[str, pl.DataFrame]:
    """Zet de tekstkolommen per recordsoort om naar de typen uit het schema.

    Args:
        frames:      Uitvoer van :func:`read_multi_record_csv`.
        schema_name: ``"analyse"`` of ``"hisbek"``.

    Returns:
        Nieuwe dict met getypeerde DataFrames; frames die niet in het schema
        staan (zoals ``MELDINGEN``) blijven onveranderd.
    """
    schema = load_schema(schema_name)
    return {
        rs: _decode_recordsoort(df, schema[rs]) if rs in schema else df
        for rs, df in frames.items()
    }
