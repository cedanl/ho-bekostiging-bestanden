"""Pseudonimisering van persoonsnummers, gelijk aan 1cijferho (#17).

Het BSN en het onderwijsnummer worden vervangen door een HMAC-SHA256-pseudoniem
met een geheime sleutel. Het algoritme, de sleutelbron en de sleuteleisen zijn
exact die van ``pseudonymize_value`` in ``cedanl/1cijferho``
(``src/eencijferho/utils/pseudonymizer.py``). Met dezelfde sleutel geeft een
BSN daardoor in beide projecten hetzelfde pseudoniem, zodat de
bekostigingsbestanden aan 1CHO te koppelen zijn — zonder dat er een leesbaar
BSN in de output staat.

Let op: dit is pseudonimisering, geen anonimisering. Wie de sleutel heeft, kan
een bekend BSN opnieuw pseudonimiseren en zo terugvinden.
"""

import hashlib
import hmac
import os
from pathlib import Path

import polars as pl

# Zelfde omgevingsvariabele als 1cijferho: één sleutel per instelling voor beide.
SLEUTEL_ENV = "EENCIJFERHO_ENCRYPT_KEY"
# Zelfde eis als 1cijferho: minstens de blokgrootte van HMAC-SHA256 (64 bytes).
MIN_SLEUTEL_BYTES = 64
PERSOON_KOLOMMEN = ("Burgerservicenummer", "Onderwijsnummer")


def laad_sleutel(
    sleutel: str | None = None,
    sleutelbestand: str | Path | None = None,
) -> bytes:
    """Bepaal de geheime sleutel; voorrang: ``sleutel`` → bestand → ``SLEUTEL_ENV``.

    Raises:
        ValueError: Als er geen sleutel is, of als die korter is dan
            ``MIN_SLEUTEL_BYTES`` bytes (UTF-8).
    """
    if sleutel is None and sleutelbestand is not None:
        sleutel = Path(sleutelbestand).read_text(encoding="utf-8").strip()
    if sleutel is None:
        sleutel = os.environ.get(SLEUTEL_ENV)
    if not sleutel:
        raise ValueError(
            "Geen pseudonimiseringssleutel gevonden. Zet de omgevingsvariabele "
            f"{SLEUTEL_ENV} (dezelfde sleutel als in 1cijferho) of geef een "
            "sleutelbestand mee."
        )
    gecodeerd = sleutel.encode("utf-8")
    if len(gecodeerd) < MIN_SLEUTEL_BYTES:
        raise ValueError(
            f"Pseudonimiseringssleutel is te kort: {len(gecodeerd)} bytes, "
            f"minimaal {MIN_SLEUTEL_BYTES} bytes vereist."
        )
    return gecodeerd


def pseudoniem(sleutel: bytes, waarde: str | None) -> str | None:
    """HMAC-SHA256-pseudoniem (hex) van één waarde; leeg blijft leeg."""
    if waarde is None or waarde == "":
        return None
    return hmac.new(sleutel, waarde.encode("utf-8"), hashlib.sha256).hexdigest()


def _pseudonimiseer_kolom(df: pl.DataFrame, kolom: str, sleutel: bytes) -> pl.Expr:
    """Vervang elke unieke waarde één keer door zijn pseudoniem."""
    uniek = df[kolom].drop_nulls().unique().to_list()
    return pl.col(kolom).replace_strict(
        uniek,
        [pseudoniem(sleutel, w) for w in uniek],
        default=None,
        return_dtype=pl.Utf8,
    )


def pseudonimiseer_frames(
    frames: dict[str, pl.DataFrame],
    sleutel: bytes,
) -> dict[str, pl.DataFrame]:
    """Pseudonimiseer de ``PERSOON_KOLOMMEN`` in elk frame waarin ze voorkomen.

    De kolomnamen blijven gelijk (zoals in 1cijferho), zodat een gepseudonimiseerd
    ``Burgerservicenummer`` direct te joinen is met dat van 1CHO.
    """
    return {
        naam: df.with_columns(
            _pseudonimiseer_kolom(df, kolom, sleutel).alias(kolom)
            for kolom in PERSOON_KOLOMMEN
            if kolom in df.columns
        )
        for naam, df in frames.items()
    }
