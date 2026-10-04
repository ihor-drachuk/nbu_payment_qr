from decimal import Decimal

from nbu_payment_qr import classify_code, is_valid_iban, normalize_code, normalize_iban, parse_amount, parse_cell_amount

VALID_IBAN = "UA693000010000000012345678901"


def test_valid_iban_passes_mod97():
    assert is_valid_iban(VALID_IBAN)


def test_iban_with_wrong_check_digits_fails():
    assert not is_valid_iban("UA703000010000000012345678901")


def test_iban_wrong_shape_fails():
    assert not is_valid_iban("UA6930000100000000123456789")  # 25 digits, needs 27
    assert not is_valid_iban("DE89370400440532013000")  # not UA
    assert not is_valid_iban("UA69300001000000001234567890A")  # letter in the digit tail


def test_normalize_iban_strips_spaces_and_uppercases():
    assert normalize_iban(" ua69 3000 0100 0000 0012 3456 7890 1 ") == VALID_IBAN
    assert normalize_iban(None) is None
    assert normalize_iban("   ") is None


def test_normalize_code_strips_whitespace():
    assert normalize_code(" 1234 5678 ") == "12345678"
    assert normalize_code(None) is None
    assert normalize_code("  ") is None


def test_classify_code_by_length():
    assert classify_code("12345678") == "edrpou"
    assert classify_code("1234567890") == "rnokpp"
    assert classify_code("123456789") == "invalid"
    assert classify_code("1234567a") == "invalid"
    assert classify_code("") == "empty"
    assert classify_code(None) == "empty"


def test_parse_amount_requires_positive():
    assert parse_amount("588.00") == Decimal("588.00")
    assert parse_amount("UAH 588,50") == Decimal("588.50")
    assert parse_amount("0") is None
    assert parse_amount("0.00") is None
    assert parse_amount(None) is None


def test_parse_cell_amount_accepts_explicit_zero():
    assert parse_cell_amount("0.00") == Decimal("0.00")
    assert parse_cell_amount("145.12") == Decimal("145.12")
    assert parse_cell_amount("10.1") == Decimal("10.1")


def test_parse_cell_amount_empty_is_none():
    assert parse_cell_amount(None) is None
    assert parse_cell_amount("") is None
    assert parse_cell_amount("   ") is None


def test_amount_parsing_normalizes_separators_and_prefix():
    assert parse_amount("1 600,00") == Decimal("1600.00")
    assert parse_cell_amount("1 600,00") == Decimal("1600.00")
    assert parse_cell_amount("uah 0,00") == Decimal("0")


def test_non_ascii_whitespace_separators_are_stripped():
    for space in (" ", " "):
        assert parse_amount(f"13{space}727,50") == Decimal("13727.50")
        assert parse_cell_amount(f"1{space}600,00") == Decimal("1600.00")
        assert normalize_iban(VALID_IBAN[:4] + space + VALID_IBAN[4:]) == VALID_IBAN
        assert normalize_code(f"1234{space}5678") == "12345678"


def test_non_ascii_digits_are_rejected():
    fullwidth = str.maketrans("0123456789", "０１２３４５６７８９")
    assert not is_valid_iban(VALID_IBAN.translate(fullwidth))
    assert classify_code("12345678".translate(fullwidth)) == "invalid"
    assert classify_code("1234567890".translate(fullwidth)) == "invalid"
    assert parse_amount("100".translate(fullwidth)) is None
    assert parse_cell_amount("100".translate(fullwidth)) is None


def test_amount_parsing_rejects_non_plain_decimals():
    for raw in ("1e2", "1e9999999", "1_000", "+5.00", "-5", "-0.00", "nan", "NaN", "inf", "1.234", "abc"):
        assert parse_amount(raw) is None, raw
        assert parse_cell_amount(raw) is None, raw
