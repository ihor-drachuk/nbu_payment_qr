"""Styled QR rendering."""

from collections.abc import Callable
from dataclasses import dataclass, field

import qrcode
from PIL import Image
from qrcode.constants import ERROR_CORRECT_M
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import RadialGradiantColorMask
from qrcode.image.styles.moduledrawers.base import QRModuleDrawer
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer, SquareModuleDrawer


@dataclass(frozen=True)
class QrStyle:
    # A consumer overlaying a logo on the QR needs ERROR_CORRECT_H; M suffices otherwise.
    error_correction: int = ERROR_CORRECT_M
    center_color: tuple[int, int, int] = (94, 53, 177)  # deep violet
    edge_color: tuple[int, int, int] = (49, 27, 146)  # indigo
    back_color: tuple[int, int, int] = (255, 255, 255)
    box_size: int = 10
    border: int = 4
    # Drawer factories, not instances: a drawer binds the image it renders into and caches
    # box_size-sized bitmaps, so one shared instance is unsafe across concurrent renders.
    module_drawer: Callable[[], QRModuleDrawer] = field(default=RoundedModuleDrawer)
    eye_drawer: Callable[[], QRModuleDrawer] = field(default=SquareModuleDrawer)


DEFAULT_STYLE = QrStyle()


def render_qr(url: str, *, style: QrStyle = DEFAULT_STYLE) -> Image.Image:
    qr = qrcode.QRCode(error_correction=style.error_correction, box_size=style.box_size, border=style.border)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=style.module_drawer(),
        eye_drawer=style.eye_drawer(),
        color_mask=RadialGradiantColorMask(back_color=style.back_color,
                                           center_color=style.center_color, edge_color=style.edge_color),
    ).convert("RGBA")
    return image
