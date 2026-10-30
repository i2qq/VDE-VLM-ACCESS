"""
vde_vlm.vision
~~~~~~~~~~~~~~
Vision and screen observation module for VirtualBox VMs.
Handles capturing screenshots, generating coordinate-grid overlays for VLMs,
detecting visual differences between steps, and optical transcription (OCR).
"""

from __future__ import annotations

import os
import tempfile
import time
from typing import Any, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from vde_vlm.vbox import run_vbox_cmd


def take_screenshot(
    vm_name_or_uuid: str,
    output_path: Optional[str] = None,
    display: int = 0,
) -> str:
    """Capture a screenshot of the specified VM display.

    Args:
        vm_name_or_uuid: Target VM.
        output_path: Destination path for the PNG. If None, saves to a temp file.
        display: Display index (default 0).

    Returns:
        Absolute path to the captured PNG.
    """
    if not output_path:
        fd, output_path = tempfile.mkstemp(prefix=f"vbox_{vm_name_or_uuid}_", suffix=".png")
        os.close(fd)

    abs_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # VBoxManage controlvm <vm> screenshotpng <file> [display]
    run_vbox_cmd("controlvm", vm_name_or_uuid, "screenshotpng", abs_path, str(display))

    if not os.path.isfile(abs_path) or os.path.getsize(abs_path) == 0:
        raise RuntimeError(f"Screenshot failed or produced empty file: {abs_path}")

    return abs_path


def add_coordinate_grid(
    image_path: str,
    output_path: Optional[str] = None,
    grid_step: int = 100,
    font_size: int = 12,
) -> str:
    """Overlay a coordinate grid with pixel markings onto an image.

    This helps Vision-Language Models (VLMs) accurately perceive spatial coordinates
    of UI elements on the VM screen.

    Args:
        image_path: Path to source screenshot.
        output_path: Destination path. Defaults to inserting '_grid' before extension.
        grid_step: Spacing in pixels between grid lines (default 100).
        font_size: Font size for coordinate numbers.

    Returns:
        Path to the annotated grid image.
    """
    if not output_path:
        root, ext = os.path.splitext(image_path)
        output_path = f"{root}_grid{ext}"

    with Image.open(image_path).convert("RGBA") as base:
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        width, height = base.size

        # Grid lines styling
        line_color = (0, 255, 255, 70)       # Cyan semi-transparent for general lines
        major_line_color = (255, 50, 50, 110) # Red for major 500px lines
        text_color = (255, 255, 0, 230)       # Yellow for high-contrast labels
        bg_box = (0, 0, 0, 160)               # Dark background badge for text

        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        # Vertical lines & X coordinates
        for x in range(0, width, grid_step):
            is_major = (x % (grid_step * 5) == 0)
            col = major_line_color if is_major else line_color
            draw.line([(x, 0), (x, height)], fill=col, width=2 if is_major else 1)

            # Label on top and bottom borders
            label = str(x)
            draw.rectangle([(x + 2, 2), (x + 32, 16)], fill=bg_box)
            draw.text((x + 4, 3), label, fill=text_color, font=font)

        # Horizontal lines & Y coordinates
        for y in range(0, height, grid_step):
            is_major = (y % (grid_step * 5) == 0)
            col = major_line_color if is_major else line_color
            draw.line([(0, y), (width, y)], fill=col, width=2 if is_major else 1)

            # Label on left border
            label = str(y)
            draw.rectangle([(2, y + 2), (32, y + 16)], fill=bg_box)
            draw.text((4, y + 3), label, fill=text_color, font=font)

        # Coordinate intersection badges every 200px
        for x in range(grid_step * 2, width - 50, grid_step * 2):
            for y in range(grid_step * 2, height - 30, grid_step * 2):
                coord_text = f"{x},{y}"
                draw.rectangle([(x + 2, y + 2), (x + 55, y + 16)], fill=bg_box)
                draw.text((x + 4, y + 3), coord_text, fill=text_color, font=font)

        # Composite base and overlay
        result = Image.alpha_composite(base, overlay).convert("RGB")
        result.save(output_path, "PNG")

    return output_path


def _get_pixels(img: Image.Image):
    """Retrieve pixel data compatible with all Pillow versions."""
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    return list(img.getdata())


def compare_screenshots(image_path_a: str, image_path_b: str, threshold: float = 0.005) -> Tuple[float, bool]:
    """Compare two screenshots to measure visual difference.

    Useful to determine whether an agent action (click/key) caused a GUI update.

    Args:
        image_path_a: Baseline image.
        image_path_b: Image after action.
        threshold: Fraction of changed pixels considered significant (default 0.5%).

    Returns:
        Tuple of (diff_ratio, has_changed).
    """
    with Image.open(image_path_a).convert("RGB") as img_a, Image.open(image_path_b).convert("RGB") as img_b:
        if img_a.size != img_b.size:
            return 1.0, True

        # Quick pixel comparison using resized grayscale copies for performance
        thumb_size = (320, 180)
        thumb_a = img_a.resize(thumb_size).convert("L")
        thumb_b = img_b.resize(thumb_size).convert("L")

        pixels_a = _get_pixels(thumb_a)
        pixels_b = _get_pixels(thumb_b)

        total = len(pixels_a)
        diff_count = sum(1 for pa, pb in zip(pixels_a, pixels_b) if abs(pa - pb) > 15)

        diff_ratio = diff_count / total
        return diff_ratio, (diff_ratio >= threshold)


def inspect_screen_state(image_path: str) -> Dict[str, Any]:
    """Analyze basic visual metrics of the screenshot.

    Returns:
        Dict containing resolution, average brightness, and whether screen is all black.
    """
    with Image.open(image_path) as img:
        width, height = img.size
        grayscale = img.convert("L")
        pixels = _get_pixels(grayscale)
        avg_brightness = sum(pixels) / max(1, len(pixels))
        is_all_black = avg_brightness < 2.0

    return {
        "width": width,
        "height": height,
        "average_brightness": round(avg_brightness, 2),
        "is_all_black": is_all_black,
        "path": os.path.abspath(image_path),
    }


def transcribe_screen(image_path: str) -> Dict[str, Any]:
    """Attempt OCR transcription if pytesseract or an OCR engine is present.

    Returns:
        Dict with text content and status.
    """
    try:
        import pytesseract  # type: ignore
        text = pytesseract.image_to_string(Image.open(image_path))
        return {"available": True, "text": text.strip()}
    except ImportError:
        return {
            "available": False,
            "text": "",
            "note": "pytesseract not installed in host Python environment. Visual VLM inspection recommended.",
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}
