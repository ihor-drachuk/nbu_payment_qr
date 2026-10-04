"""Ukrainian IBAN (ISO 13616 MOD-97), EDRPOU/RNOKPP and amount parsing. Pure functions, no I/O."""

import re
from decimal import Decimal
from typing import Literal

# re.ASCII: a plain \d also matches non-ASCII digits, which CP1251 turns into '?' in the payload.
_IBAN_RE = re.compile(r"UA\d{27}", re.ASCII)
_EDRPOU_RE = re.compile(r"\d{8}", re.ASCII)
_RNOKPP_RE = re.compile(r"\d{10}", re.ASCII)
# Decimal() alone would also accept exponent (1e2), underscores (1_000), signs and inf/nan —
# the regex gates those out before construction.
_AMOUNT_RE = re.compile(r"\d+(\.\d{1,2})?", re.ASCII)


def normalize_iban(raw: str | None) -> str | None:
    if raw is None:
        return None
    iban = re.sub(r"\s+", "", raw).upper()
    return iban or None


def is_valid_iban(iban: str) -> bool:
    if not _IBAN_RE.fullmatch(iban):
        return False
    # ISO 13616 MOD-97: move the first 4 chars to the end, letters -> 10..35 (U=30, A=10), remainder must be 1.
    rearranged = iban[4:] + iban[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(digits) % 97 == 1


def normalize_code(raw: str | None) -> str | None:
    if raw is None:
        return None
    code = re.sub(r"\s+", "", raw)
    return code or None


CodeKind = Literal["edrpou", "rnokpp", "invalid", "empty"]


def classify_code(code: str | None) -> CodeKind:
    if not code:
        return "empty"
    if _EDRPOU_RE.fullmatch(code):
        return "edrpou"
    if _RNOKPP_RE.fullmatch(code):
        return "rnokpp"
    return "invalid"


def _parse_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    cleaned = raw.strip().upper().removeprefix("UAH")
    cleaned = re.sub(r"\s", "", cleaned).replace(",", ".")
    if not _AMOUNT_RE.fullmatch(cleaned):
        return None
    return Decimal(cleaned)  # _AMOUNT_RE guarantees a Decimal-parseable string


def parse_amount(raw: str | None) -> Decimal | None:
    """Payment amount where zero is not a valid value (must be > 0)."""
    value = _parse_decimal(raw)
    if value is None or value <= 0:
        return None
    return value


def parse_cell_amount(raw: str | None) -> Decimal | None:
    """Table-cell amount where an explicit 0.00 is valid; garbage/negative/empty -> None."""
    return _parse_decimal(raw)
