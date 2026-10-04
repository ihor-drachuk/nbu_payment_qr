<div align="center">
  <h3>nbu_payment_qr</h3>
  <p><b>Ukrainian NBU payment QR codes for Python</b></p>

  [![CI](https://github.com/ihor-drachuk/nbu_payment_qr/actions/workflows/ci.yml/badge.svg)](https://github.com/ihor-drachuk/nbu_payment_qr/actions/workflows/ci.yml)
  ![Python](https://img.shields.io/badge/python-3.12+-blue)
  ![License](https://img.shields.io/badge/license-MIT-green)
</div>

Builds the NBU payment QR payload and its `https://bank.gov.ua/qr/...` deep link, renders a styled QR image, and validates Ukrainian payment requisites. The payload is 14 lines in the BCD/UCT format, CP1251-encoded and wrapped in base64url. A Ukrainian banking app that scans the QR pre-fills an IBAN payment: recipient, IBAN, EDRPOU/RNOKPP, amount and purpose.

## Installation

As a git submodule with a path requirement:

```sh
git submodule add https://github.com/ihor-drachuk/nbu_payment_qr.git libs/nbu_payment_qr
echo ./libs/nbu_payment_qr >> requirements.txt
```

Without a submodule, pin a commit in `requirements.txt`:

```
nbu_payment_qr @ https://github.com/ihor-drachuk/nbu_payment_qr/archive/<commit>.tar.gz
```

Dependencies: `qrcode`, `pillow`.

## Usage

```python
from decimal import Decimal
from nbu_payment_qr import build_nbu_qr

result = build_nbu_qr(name='ТОВ "ОРІОН-ПЛЮС"', iban="UA693000010000000012345678901",
                      amount=Decimal("13727"), code="12345678", purpose="Рахунок № 1024")
result.url        # https://bank.gov.ua/qr/... (encoded in the QR)
result.mono_url   # https://send.monobank.ua/qr/... (same payload)
result.payload    # the final 14-line string, e.g. for an idempotency hash
result.png        # PNG bytes
result.image      # PIL image (RGBA)
```

### Style

`QrStyle` sets the error correction level, the colors, the module size, the border and the module drawers. A logo drawn over the QR needs error correction H:

```python
from qrcode.constants import ERROR_CORRECT_H
from nbu_payment_qr import QrStyle

style = QrStyle(error_correction=ERROR_CORRECT_H, center_color=(30, 90, 168), edge_color=(18, 130, 120))
build_nbu_qr(iban="UA693000010000000012345678901", style=style)
```

## Error contract

`build_nbu_qr` either returns the QR of a correct payment or raises `ValueError`:

- The IBAN is whitespace-stripped and upper-cased. It must be `UA` plus 27 digits and pass the MOD-97 check.
- The code is whitespace-stripped. It must be empty, 8 digits (EDRPOU) or 10 digits (RNOKPP).
- The amount must be finite, within 0..9 999 999.99, with at most 2 decimals. Round it before the call.
- All fields except the purpose must fit the 331-byte payload limit. Otherwise the error is `PayloadOverflowError`, a `ValueError` subclass.

Only the purpose is ever truncated to fit. `truncated_purpose` reports it.

## Other exports

| Symbol | Purpose |
|---|---|
| `purpose_budget_bytes(name, iban, code)` | bytes left for the purpose at the widest amount, to validate a configured purpose at startup |
| `is_valid_iban`, `normalize_iban` | IBAN check and normalization |
| `classify_code`, `normalize_code`, `CodeKind` | EDRPOU/RNOKPP check and normalization |
| `parse_amount`, `parse_cell_amount` | strict amount parsing (> 0, and ≥ 0 for table cells) |
| `format_amount` | the payload's amount line |
| `single_line`, `to_cp1251_bytes` | one-line collapse and CP1251 encoding, as the payload applies them |
| `render_qr`, `DEFAULT_STYLE` | rendering a URL with a style, and the default style |
| `MAX_AMOUNT`, `MAX_PAYLOAD_BYTES`, `NBU_QR_PREFIX`, `MONO_QR_PREFIX`, `mono_url` | format constants and the Monobank link |

## Development

```sh
python -m venv .venv
.venv/Scripts/python -m pip install qrcode pillow pytest   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m pytest tests -v
```

The decode round-trip test also needs `zxing-cpp`. Without it, the test is skipped.

## License

MIT
