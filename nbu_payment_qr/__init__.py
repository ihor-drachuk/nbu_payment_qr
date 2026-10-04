"""NBU payment QR: payload building, styled rendering, Ukrainian IBAN/EDRPOU validation.

The payload is 14 positional lines, CP1251-encoded before base64url, wrapped into the
https://bank.gov.ua/qr/ deep link.
"""

import io
from dataclasses import dataclass
from decimal import Decimal

from PIL import Image

from .iban import (
    CodeKind,
    classify_code,
    is_valid_iban,
    normalize_code,
    normalize_iban,
    parse_amount,
    parse_cell_amount,
)
from .payload import (
    MAX_AMOUNT,
    MAX_PAYLOAD_BYTES,
    MONO_QR_PREFIX,
    NBU_QR_PREFIX,
    PayloadOverflowError,
    _remaining_purpose_budget,
    build_payload,
    encode_url,
    format_amount,
    mono_url,
    purpose_budget_bytes,
    single_line,
    to_cp1251_bytes,
)
from .render import DEFAULT_STYLE, QrStyle, render_qr

__all__ = [
    "CodeKind", "classify_code", "is_valid_iban", "normalize_code", "normalize_iban",
    "parse_amount", "parse_cell_amount",
    "MAX_AMOUNT", "MAX_PAYLOAD_BYTES", "MONO_QR_PREFIX", "NBU_QR_PREFIX", "PayloadOverflowError",
    "format_amount", "mono_url", "purpose_budget_bytes", "single_line", "to_cp1251_bytes",
    "DEFAULT_STYLE", "QrStyle", "render_qr",
    "QrResult", "build_nbu_qr",
]


@dataclass(frozen=True, eq=False)  # PIL images compare pixel-deep and are unhashable
class QrResult:
    image: Image.Image  # RGBA QR, no logo/caption overlay
    url: str  # https://bank.gov.ua/qr/... — the value encoded in the QR
    payload: str  # the final 14-line string (after collapsing/truncation) — hash this for idempotency
    truncated_purpose: bool

    @property
    def mono_url(self) -> str:
        return mono_url(self.url)

    @property
    def png(self) -> bytes:
        buffer = io.BytesIO()
        self.image.convert("RGB").save(buffer, format="PNG")
        return buffer.getvalue()


def build_nbu_qr(*, name: str | None = None, iban: str, amount: Decimal | None = None,
                 code: str | None = None, purpose: str | None = None,
                 style: QrStyle = DEFAULT_STYLE) -> QrResult:
    """Raise ValueError on requisites that cannot form a correct payment.

    IBAN and code are normalized here (whitespace stripped, IBAN upper-cased) and validated;
    name and purpose are collapsed to single-line text. The purpose is truncated to the byte
    budget; nothing else ever is. PayloadOverflowError means the other fields alone exceed the payload limit.
    """
    iban = normalize_iban(iban) or ""
    if not is_valid_iban(iban):
        raise ValueError(f"Invalid IBAN: {iban!r}")
    code = normalize_code(code) or ""
    if classify_code(code) == "invalid":
        raise ValueError(f"Code must be 8 (EDRPOU) or 10 (RNOKPP) digits: {code!r}")
    name = single_line(name or "")
    purpose = single_line(purpose or "")
    amount_line = format_amount(amount)

    budget = _remaining_purpose_budget(name, iban, amount_line, code)
    if budget < 0:
        raise PayloadOverflowError(f"Fixed payload fields exceed the {MAX_PAYLOAD_BYTES}-byte limit by {-budget} bytes")
    # CP1251 is single-byte (replacement '?' included), so the character count of the purpose
    # can be compared against and sliced by the byte budget directly.
    truncated = len(purpose) > budget
    if truncated:
        purpose = purpose[:budget]

    payload = build_payload(name, iban, amount_line, code, purpose)
    url = encode_url(payload)
    return QrResult(image=render_qr(url, style=style), url=url, payload=payload, truncated_purpose=truncated)
