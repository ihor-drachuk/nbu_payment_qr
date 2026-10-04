from decimal import Decimal

import pytest
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_M

from nbu_payment_qr import QrStyle, build_nbu_qr, render_qr

URL = "https://bank.gov.ua/qr/QkNECjAwMgoyClVDVAoKClVBNjkzMDAwMDEwMDAwMDAwMDEyMzQ1Njc4OTAxCgoKCgoKCgo"


def sample_qr():
    return build_nbu_qr(name="Name", iban="UA693000010000000012345678901", amount=Decimal("1"),
                        code="12345678", purpose="test")


def test_build_nbu_qr_produces_png():
    assert sample_qr().png.startswith(b"\x89PNG")


def test_image_is_rgba_square():
    result = sample_qr()
    assert result.image.mode == "RGBA"
    assert result.image.width == result.image.height


def test_error_correction_levels_produce_different_images():
    image_m = render_qr(URL, style=QrStyle(error_correction=ERROR_CORRECT_M))
    image_h = render_qr(URL, style=QrStyle(error_correction=ERROR_CORRECT_H))
    # H stores ~30% redundancy vs M's ~15%, so the module grid (and image size) grows.
    assert image_h.width > image_m.width


def test_back_color_is_honored():
    image = render_qr(URL, style=QrStyle(back_color=(255, 0, 0)))
    # The border is always background-colored.
    assert image.getpixel((1, 1))[:3] == (255, 0, 0)


def test_box_size_scales_image_proportionally():
    small = render_qr(URL, style=QrStyle(box_size=5))
    large = render_qr(URL, style=QrStyle(box_size=10))
    assert large.width == small.width * 2


def test_border_adds_module_sized_margin():
    tight = render_qr(URL, style=QrStyle(border=4, box_size=10))
    wide = render_qr(URL, style=QrStyle(border=6, box_size=10))
    assert wide.width == tight.width + 2 * 2 * 10  # 2 extra border modules on each side


def test_render_is_deterministic_across_calls():
    assert render_qr(URL).tobytes() == render_qr(URL).tobytes()


def test_default_style_is_violet_gradient_with_error_correction_m():
    from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer, SquareModuleDrawer

    from nbu_payment_qr import DEFAULT_STYLE

    assert DEFAULT_STYLE == QrStyle(error_correction=ERROR_CORRECT_M, center_color=(94, 53, 177),
                                    edge_color=(49, 27, 146), back_color=(255, 255, 255), box_size=10, border=4,
                                    module_drawer=RoundedModuleDrawer, eye_drawer=SquareModuleDrawer)


def test_style_drawers_are_factories_yielding_fresh_instances():
    style = QrStyle()
    assert style.module_drawer() is not style.module_drawer()
    assert style.eye_drawer() is not style.eye_drawer()


def test_png_bytes_decode_as_rgb_image():
    import io

    from PIL import Image

    with Image.open(io.BytesIO(sample_qr().png)) as image:
        assert image.mode == "RGB"


def test_rendered_qr_decodes_back_to_the_encoded_url():
    zxingcpp = pytest.importorskip("zxingcpp")
    result = sample_qr()
    decoded = zxingcpp.read_barcode(result.image.convert("RGB"))
    assert decoded is not None and decoded.valid
    assert decoded.text == result.url
