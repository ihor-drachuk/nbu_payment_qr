import base64
from decimal import Decimal

import pytest

from nbu_payment_qr import (
    MAX_AMOUNT,
    MAX_PAYLOAD_BYTES,
    MONO_QR_PREFIX,
    NBU_QR_PREFIX,
    PayloadOverflowError,
    build_nbu_qr,
    format_amount,
    mono_url,
    parse_amount,
    purpose_budget_bytes,
    single_line,
    to_cp1251_bytes,
)

POC_NAME = 'ТОВ "ОРІОН-ПЛЮС"'
POC_IBAN = "UA693000010000000012345678901"
POC_CODE = "12345678"
POC_AMOUNT = Decimal("13727")
POC_PURPOSE = "Рахунок на оплату № 1024 від 30 червня 2026 р."

POC_EXPECTED_PAYLOAD = (
    "BCD\n002\n2\nUCT\n\n"
    'ТОВ "ОРІОН-ПЛЮС"\n'
    "UA693000010000000012345678901\n"
    "UAH13727\n"
    "12345678\n\n\n"
    "Рахунок на оплату № 1024 від 30 червня 2026 р.\n\n"
)


def poc_qr(**overrides):
    kwargs = dict(name=POC_NAME, iban=POC_IBAN, amount=POC_AMOUNT, code=POC_CODE, purpose=POC_PURPOSE)
    kwargs.update(overrides)
    return build_nbu_qr(**kwargs)


def decode_payload(url: str) -> str:
    b64 = url.removeprefix(NBU_QR_PREFIX)
    padded = b64 + "=" * (-len(b64) % 4)
    return base64.urlsafe_b64decode(padded).decode("cp1251")


def test_poc_example_payload_matches_reference():
    result = poc_qr()
    assert decode_payload(result.url) == POC_EXPECTED_PAYLOAD
    assert not result.truncated_purpose


def test_result_payload_equals_decoded_url():
    result = poc_qr()
    assert result.payload == decode_payload(result.url)


def test_url_shape():
    result = poc_qr()
    assert result.url.startswith(NBU_QR_PREFIX)
    b64 = result.url.removeprefix(NBU_QR_PREFIX)
    assert "=" not in b64
    assert "+" not in b64
    assert "/" not in b64


def test_mono_url_shares_payload_on_mono_host():
    result = poc_qr()
    payload = result.url.removeprefix(NBU_QR_PREFIX)
    assert result.mono_url == MONO_QR_PREFIX + payload
    assert decode_payload(result.url) == decode_payload(result.mono_url.replace(MONO_QR_PREFIX, NBU_QR_PREFIX))


def test_mono_url_function_swaps_only_the_prefix():
    assert mono_url(NBU_QR_PREFIX + "abc") == MONO_QR_PREFIX + "abc"


def test_payload_has_14_lines_with_empty_optional_fields():
    result = build_nbu_qr(iban=POC_IBAN)
    lines = decode_payload(result.url).split("\n")
    assert lines == ["BCD", "002", "2", "UCT", "", "", POC_IBAN, "", "", "", "", "", "", ""]


def test_iban_with_whitespace_is_stripped_not_shifted():
    result = poc_qr(iban="UA69 3000\n0100 0000 0012 3456 7890 1")
    lines = decode_payload(result.url).split("\n")
    assert len(lines) == 14
    assert lines[6] == POC_IBAN


def test_lowercase_iban_is_uppercased():
    result = poc_qr(iban=POC_IBAN.lower())
    assert decode_payload(result.url).split("\n")[6] == POC_IBAN


def test_invalid_iban_raises():
    with pytest.raises(ValueError, match="IBAN"):
        poc_qr(iban="UA703000010000000012345678901")  # wrong check digits
    with pytest.raises(ValueError, match="IBAN"):
        poc_qr(iban="DE89370400440532013000")


def test_non_ascii_digits_in_iban_and_code_raise():
    fullwidth = str.maketrans("0123456789", "０１２３４５６７８９")
    with pytest.raises(ValueError, match="IBAN"):
        poc_qr(iban=POC_IBAN.translate(fullwidth))
    with pytest.raises(ValueError, match="Code"):
        poc_qr(code=POC_CODE.translate(fullwidth))


def test_code_with_whitespace_is_stripped():
    result = poc_qr(code="1234 5678 90")
    assert decode_payload(result.url).split("\n")[8] == "1234567890"


def test_malformed_code_raises():
    with pytest.raises(ValueError, match="Code"):
        poc_qr(code="123456789")  # 9 digits is neither EDRPOU nor RNOKPP
    with pytest.raises(ValueError, match="Code"):
        poc_qr(code=POC_IBAN)


def test_empty_code_is_allowed():
    result = poc_qr(code=None)
    assert decode_payload(result.url).split("\n")[8] == ""


def test_format_amount_integer_has_no_decimals():
    assert format_amount(Decimal("13727")) == "UAH13727"
    assert format_amount(Decimal("13727.00")) == "UAH13727"


def test_format_amount_fractional_uses_dot_and_two_decimals():
    assert format_amount(Decimal("13727.5")) == "UAH13727.50"


def test_format_amount_none_is_empty():
    assert format_amount(None) == ""


def test_format_amount_zero_is_uah0():
    assert format_amount(Decimal("0")) == "UAH0"


def test_format_amount_rejects_negative():
    with pytest.raises(ValueError):
        format_amount(Decimal("-1"))


def test_format_amount_rejects_over_max():
    with pytest.raises(ValueError):
        format_amount(MAX_AMOUNT + Decimal("0.01"))


def test_format_amount_rejects_more_than_two_decimals():
    with pytest.raises(ValueError):
        format_amount(Decimal("1.234"))


def test_format_amount_rejects_non_finite_with_valueerror():
    for raw in ("NaN", "-NaN", "sNaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError):
            format_amount(Decimal(raw))


def test_cp1251_encoding_of_ukrainian_letters():
    assert to_cp1251_bytes("Єє Іі Її Ґґ №") == b"\xaa\xba \xb2\xb3 \xaf\xbf \xa5\xb4 \xb9"


def test_cp1251_unmappable_char_becomes_question_mark():
    assert to_cp1251_bytes("оплата 💳") == to_cp1251_bytes("оплата ") + b"?"


def test_single_line_collapses_runs_and_strips_edges():
    assert single_line("  a\t b\r\nc  ") == "a b c"
    assert single_line("") == ""


def test_long_purpose_truncated_to_fit_limit():
    long_purpose = "Оплата за товар згідно рахунку № 12345 " * 20
    result = poc_qr(purpose=long_purpose)
    assert result.truncated_purpose
    payload = decode_payload(result.url)
    assert len(to_cp1251_bytes(payload)) == MAX_PAYLOAD_BYTES
    lines = payload.split("\n")
    assert len(lines) == 14
    assert lines[5] == POC_NAME
    assert lines[6] == POC_IBAN
    assert lines[7] == "UAH13727"
    assert lines[8] == POC_CODE
    assert long_purpose.startswith(lines[11])


def test_short_purpose_not_truncated():
    result = poc_qr()
    payload = decode_payload(result.url)
    assert len(to_cp1251_bytes(payload)) <= MAX_PAYLOAD_BYTES
    assert not result.truncated_purpose


def test_multiline_purpose_collapsed_to_keep_14_payload_lines():
    result = poc_qr(purpose="Оплата за товар\nзгідно рахунку\r\n№ 123")
    lines = decode_payload(result.url).split("\n")
    assert len(lines) == 14
    assert lines[11] == "Оплата за товар згідно рахунку № 123"
    assert not result.truncated_purpose


def test_multiline_name_collapsed():
    result = poc_qr(name='ТОВ\n"НАЗВА"', amount=None, purpose=None)
    lines = decode_payload(result.url).split("\n")
    assert len(lines) == 14
    assert lines[5] == 'ТОВ "НАЗВА"'


def test_oversized_base_fields_raise_overflow_error():
    with pytest.raises(PayloadOverflowError):
        poc_qr(name="А" * 400, purpose=None)


def test_amounts_accepted_by_parse_amount_within_max_always_build():
    for raw in ("1", "0.01", "13727", "13727.5", "007.50", "UAH 1 600,00", str(MAX_AMOUNT)):
        amount = parse_amount(raw)
        assert amount is not None and amount <= MAX_AMOUNT, raw
        assert decode_payload(build_nbu_qr(iban=POC_IBAN, amount=amount).url).split("\n")[7] == format_amount(amount)


def test_overflow_error_is_a_value_error():
    assert issubclass(PayloadOverflowError, ValueError)


def test_invalid_requisites_are_not_overflow_errors():
    for overrides in (dict(iban="UA703000010000000012345678901"), dict(code="123"), dict(code="１２３４５６７８"),
                      dict(amount=Decimal("1.234")), dict(amount=MAX_AMOUNT + Decimal("0.01"))):
        with pytest.raises(ValueError) as error:
            poc_qr(**overrides)
        assert not isinstance(error.value, PayloadOverflowError), overrides


def base_bytes_without_purpose(name: str) -> int:
    return len(to_cp1251_bytes("\n".join(["BCD", "002", "2", "UCT", "", name, POC_IBAN, "UAH13727", POC_CODE,
                                          "", "", "", "", ""])))


def test_base_exactly_at_limit_builds_with_empty_purpose():
    name = "А" * (400 - (base_bytes_without_purpose("А" * 400) - MAX_PAYLOAD_BYTES))
    assert base_bytes_without_purpose(name) == MAX_PAYLOAD_BYTES
    result = poc_qr(name=name, purpose=None)
    assert len(to_cp1251_bytes(result.payload)) == MAX_PAYLOAD_BYTES


def test_base_one_byte_over_limit_raises():
    name = "А" * (401 - (base_bytes_without_purpose("А" * 400) - MAX_PAYLOAD_BYTES))
    assert base_bytes_without_purpose(name) == MAX_PAYLOAD_BYTES + 1
    with pytest.raises(PayloadOverflowError):
        poc_qr(name=name, purpose=None)


def test_positional_call_is_rejected():
    with pytest.raises(TypeError):
        build_nbu_qr(POC_NAME, POC_IBAN)  # noqa: the keyword-only contract is the point


def test_qr_result_is_hashable_with_identity_semantics():
    first = poc_qr()
    second = poc_qr()
    assert first != second
    assert len({first, second}) == 2


def test_truncated_payload_field_matches_truncated_url_content():
    long_purpose = "Оплата за товар згідно рахунку № 12345 " * 20
    result = poc_qr(purpose=long_purpose)
    assert result.payload == decode_payload(result.url)


def test_purpose_budget_bytes_known_vector():
    # Without the purpose, the payload is 89 bytes at the widest amount line UAH9999999.99. 331 - 89 = 242.
    assert purpose_budget_bytes(POC_NAME, POC_IBAN, POC_CODE) == 242


def test_purpose_budget_normalizes_iban_like_the_builder():
    clean = purpose_budget_bytes(POC_NAME, POC_IBAN, POC_CODE)
    spaced = purpose_budget_bytes(POC_NAME, "UA69 3000 0100 0000 0012 3456 7890 1", "1234 5678")
    assert spaced == clean


def test_purpose_budget_raises_on_base_overflow_like_the_builder():
    with pytest.raises(PayloadOverflowError):
        purpose_budget_bytes("А" * 400, POC_IBAN, POC_CODE)


def test_py_typed_marker_ships_with_the_package():
    from pathlib import Path

    import nbu_payment_qr

    assert (Path(nbu_payment_qr.__file__).parent / "py.typed").exists()


def test_purpose_budget_uses_widest_amount_line():
    budget = purpose_budget_bytes(POC_NAME, POC_IBAN, POC_CODE)
    result = poc_qr(amount=MAX_AMOUNT, purpose="а" * budget)
    assert not result.truncated_purpose
    assert len(to_cp1251_bytes(result.payload)) == MAX_PAYLOAD_BYTES


def test_purpose_one_char_over_budget_is_truncated_to_exactly_the_limit():
    budget = purpose_budget_bytes(POC_NAME, POC_IBAN, POC_CODE)
    result = poc_qr(amount=MAX_AMOUNT, purpose="а" * (budget + 1))
    assert result.truncated_purpose
    assert len(to_cp1251_bytes(result.payload)) == MAX_PAYLOAD_BYTES


def test_zero_amount_renders_uah0_by_design():
    # parse_amount treats 0 as invalid input, but an explicit Decimal(0) amount is the caller's
    # decision and renders as UAH0 — pinned so the divergence stays deliberate.
    result = poc_qr(amount=Decimal("0"))
    assert decode_payload(result.url).split("\n")[7] == "UAH0"
