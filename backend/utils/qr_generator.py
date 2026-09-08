"""
QR code generation utilities for pairing.
"""

import logging
import os

import qrcode

logger = logging.getLogger(__name__)


def _build_qr_code(url: str, size: int) -> qrcode.QRCode:
    """Build a QR code configured for a URL."""
    if not url:
        raise ValueError("URL must not be empty")
    if size <= 0:
        raise ValueError("QR code size must be greater than zero")

    qr_code = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=4,
    )
    qr_code.add_data(url)
    qr_code.make(fit=True)
    return qr_code


def generate_qr_code(url: str, output_path: str = "qr_code.png", size: int = 10) -> None:
    """
    Generate a QR code for the given URL.
    
    Args:
        url: URL to encode in QR code
        output_path: Path to save QR code image
        size: QR code box size (larger = bigger image)
    """
    try:
        qr_code = build_and_display_qr_ascii(url)
        output_directory = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(output_directory, exist_ok=True)
        qr_code.make_image(fill_color="black", back_color="white").save(output_path)
        logger.info("QR code saved to %s", output_path)
    except (OSError, ValueError) as error:
        logger.error("Error generating QR code: %s", error)
        raise



def build_and_display_qr_ascii(url: str):
    """
    Display QR code as ASCII art in terminal.
    
    Args:
        url: URL to encode
    """
    qr_code = _build_qr_code(url, size=10)
    logger.info("Displaying QR code for %s", url)
    print(f"URL: {url}")
    for row in qr_code.get_matrix():
        print("".join("⬜" if module else "⬛" for module in row))
    return qr_code
