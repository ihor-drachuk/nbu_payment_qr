"""NBU payment payload: 14 positional lines, CP1251-encoded, base64url-wrapped into a deep link."""

import base64
import re
from decimal import Decimal

from .iban import normalize_code, normalize_iban

NBU_QR_PREFIX = "https://bank.gov.ua/qr/"
MONO_QR_PREFIX = "https://send.monobank.ua/qr/"  # same payload; opens the payment straight in monobank
MAX_PAYLOAD_BYTES = 331  # NBU limit, measured on the CP1251 bytes before base64
MAX_AMOUNT = Decimal("9999999.99")  # ~10 M UAH; bounds the amount line so the purpose budget is exact


class PayloadOverflowError(ValueError):
    """The fields other than the purpose do not fit MAX_PAYLOAD_BYTES."""


def to_cp1251_bytes(text: str) -> bytes:
    return text.encode("cp1251", errors="replace")  # unmappable chars become '?'


def format_amount(amount: Decimal | None) -> str:
    if amount is None:
        return ""
    if not amount.is_finite() or amount < 0 or amount > MAX_AMOUNT or amount != amount.quantize(Decimal("0.01")):
        # Never silently coerce a payment amount.
        raise ValueError(f"Amount must be within 0..{MAX_AMOUNT} with at most 2 decimals: {amount}")
    if amount == amount.to_integral_value():
        return f"UAH{int(amount)}"
    return f"UAH{amount:.2f}"


_WIDEST_AMOUNT_LINE = format_amount(MAX_AMOUNT)


def build_payload(name: str, iban: str, amount_line: str, code: str, purpose: str) -> str:
    # 14 lines in the fixed NBU order; empty fields stay as empty lines.
    lines = ["BCD", "002", "2", "UCT", "", name, iban, amount_line, code, "", "", purpose, "", ""]
    return "\n".join(lines)


def single_line(text: str) -> str:
    # Banking apps read the payload positionally, so a field value must not introduce extra lines.
    return re.sub(r"\s+", " ", text).strip()


def _remaining_purpose_budget(name: str, iban: str, amount_line: str, code: str) -> int:
    """Bytes left for the purpose given already-normalized fields; negative when the base overflows."""
    base = build_payload(name, iban, amount_line, code, "")
    return MAX_PAYLOAD_BYTES - len(to_cp1251_bytes(base))


def purpose_budget_bytes(name: str, iban: str, code: str) -> int:
    """Bytes left for the purpose at the widest possible amount.

    Raises PayloadOverflowError when the other fields alone exceed MAX_PAYLOAD_BYTES.
    """
    budget = _remaining_purpose_budget(single_line(name), normalize_iban(iban) or "",
                                       _WIDEST_AMOUNT_LINE, normalize_code(code) or "")
    if budget < 0:
        raise PayloadOverflowError(f"Fixed payload fields exceed the {MAX_PAYLOAD_BYTES}-byte limit by {-budget} bytes")
    return budget


def encode_url(payload: str) -> str:
    b64 = base64.urlsafe_b64encode(to_cp1251_bytes(payload)).decode("ascii").rstrip("=")
    return NBU_QR_PREFIX + b64


def mono_url(url: str) -> str:
    return MONO_QR_PREFIX + url.removeprefix(NBU_QR_PREFIX)
