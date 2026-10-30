"""
vde_vlm.vision
~~~~~~~~~~~~~~
Vision and screen observation module for VirtualBox VMs.
Handles capturing screenshots into rolling memory/disk buffers (zero disk shredding),
generating clean Google Stitch-style collaborative cursor overlays and subtle rulers,
detecting visual differences between steps, and optical transcription (OCR).
"""

from __future__ import annotations

import glob
import os
import shutil
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from vde_vlm.vbox import run_vbox_cmd

_SCREENSHOT_LOCK = threading.Lock()

# Fixed rolling cache directory to prevent disk bloating
_DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".vde_vlm", "cache")


def get_cache_dir() -> str:
    """Return the persistent directory for rolling screen buffers."""
    os.makedirs(_DEFAULT_CACHE_DIR, exist_ok=True)
    return _DEFAULT_CACHE_DIR


def clean_temp_artifacts() -> int:
    """Remove stale temporary screenshot files from system temp."""
    cleaned = 0
    temp_dir = tempfile.gettempdir()
    patterns = [
        os.path.join(temp_dir, "vbox_*.*"),
        os.path.join(_DEFAULT_CACHE_DIR, "tmp_*.*"),
    ]
    for pattern in patterns:
        for f in glob.glob(pattern):
            try:
                os.remove(f)
                cleaned += 1
            except Exception:
                pass
    return cleaned


def get_rolling_screen_path(vm_name_or_uuid: str, annotated: bool = False) -> str:
    """Get the path to a single, persistent rolling image file for this VM."""
    clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in vm_name_or_uuid)
    suffix = "_annotated.png" if annotated else ".png"
    return os.path.join(get_cache_dir(), f"live_{clean_name}{suffix}")


def take_screenshot(
    vm_name_or_uuid: str,
    output_path: Optional[str] = None,
    display: int = 0,
    use_rolling_cache: bool = True,
) -> str:
    """Capture a screenshot of the specified VM display.

    By default writes to a single rolling cache file, completely avoiding disk shredding.

    Args:
        vm_name_or_uuid: Target VM.
        output_path: Explicit destination path. If omitted and use_rolling_cache is True,
                     overwrites the persistent rolling file.
        display: Display index (default 0).
        use_rolling_cache: If True, uses the fixed rolling cache file.

    Returns:
        Absolute path to the captured PNG.
    """
    if not output_path:
        if use_rolling_cache:
            output_path = get_rolling_screen_path(vm_name_or_uuid, annotated=False)
        else:
            fd, output_path = tempfile.mkstemp(prefix=f"vbox_{vm_name_or_uuid}_", suffix=".png")
            os.close(fd)

    abs_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # VBoxManage controlvm <vm> screenshotpng <file> [display]
    with _SCREENSHOT_LOCK:
        run_vbox_cmd("controlvm", vm_name_or_uuid, "screenshotpng", abs_path, str(display))

    if not os.path.isfile(abs_path) or os.path.getsize(abs_path) == 0:
        raise RuntimeError(f"Screenshot failed or produced empty file: {abs_path}")

    return abs_path


def add_coordinate_grid(
    image_path: str,
    output_path: Optional[str] = None,
    grid_step: int = 100,
    style: str = "stitch",  # 'stitch' (clean & subtle) or 'dense'
) -> str:
    """Overlay a clean, modern coordinate grid that does NOT obstruct readability.

    In 'stitch' style:
      - Uses ultra-light, subtle guides (15% opacity) so text and UI remain completely legible.
      - Places non-obtrusive coordinate tags at borders and corner intersections.
    """
    if not output_path:
        root, ext = os.path.splitext(image_path)
        output_path = f"{root}_grid{ext}"

    with Image.open(image_path).convert("RGBA") as base:
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        width, height = base.size

        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        if style == "stitch":
            # Subtle, sleek Google Stitch-style guides
            line_col = (130, 160, 255, 30)         # Ultra-faint lavender guide
            major_line_col = (100, 200, 255, 60)   # Faint cyan for 500px steps
            badge_bg = (18, 20, 32, 200)           # Polished dark rounded pill
            badge_text = (140, 210, 255, 240)      # Soft bright cyan
            tick_col = (120, 180, 255, 160)

            # Draw outer framing border ticks
            for x in range(0, width, grid_step):
                is_major = (x % 500 == 0)
                draw.line([(x, 0), (x, height)], fill=major_line_col if is_major else line_col, width=1)
                # Border tick marks
                draw.line([(x, 0), (x, 8)], fill=tick_col, width=2)
                draw.line([(x, height - 8), (x, height)], fill=tick_col, width=2)
                # Coordinate badges along top border
                if x > 0 and x < width - 40:
                    draw.rectangle([(x + 2, 2), (x + 36, 16)], fill=badge_bg)
                    draw.text((x + 4, 3), f"{x}", fill=badge_text, font=font)

            for y in range(0, height, grid_step):
                is_major = (y % 500 == 0)
                draw.line([(0, y), (width, y)], fill=major_line_col if is_major else line_col, width=1)
                # Border tick marks
                draw.line([(0, y), (8, y)], fill=tick_col, width=2)
                draw.line([(width - 8, y), (width, y)], fill=tick_col, width=2)
                # Coordinate badges along left border
                if y > 0 and y < height - 20:
                    draw.rectangle([(2, y + 2), (36, y + 16)], fill=badge_bg)
                    draw.text((4, y + 3), f"{y}", fill=badge_text, font=font)

        else:
            # Dense high-contrast mode
            for x in range(0, width, grid_step):
                draw.line([(x, 0), (x, height)], fill=(0, 255, 255, 70), width=1)
            for y in range(0, height, grid_step):
                draw.line([(0, y), (width, y)], fill=(0, 255, 255, 70), width=1)

        result = Image.alpha_composite(base, overlay).convert("RGB")
        result.save(output_path, "PNG")

    return output_path


def draw_agent_cursor(
    image_path: str,
    x: int,
    y: int,
    output_path: Optional[str] = None,
    label: str = "Gemini",
    is_click: bool = False,
) -> str:
    """Stamp a Google Stitch-style collaborative AI cursor badge onto an image.

    Renders a colored arrow pointer, an animated click ripple (if click=True),
    and a prominent floating name badge (e.g. '🤖 Gemini').
    """
    if not output_path:
        root, ext = os.path.splitext(image_path)
        output_path = f"{root}_cursor{ext}"

    with Image.open(image_path).convert("RGBA") as base:
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Stitch Agent Theme Colors (Google Purple / Indigo beacon)
        cursor_color = (138, 75, 255, 255)       # Vibrant violet
        ripple_color = (180, 120, 255, 140)      # Expanding glow
        badge_bg = (138, 75, 255, 230)           # Solid pill
        badge_text = (255, 255, 255, 255)

        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        # 1. Click ripple effect
        if is_click:
            draw.ellipse([(x - 14, y - 14), (x + 14, y + 14)], outline=ripple_color, width=3)
            draw.ellipse([(x - 6, y - 6), (x + 6, y + 6)], fill=(255, 255, 255, 180))

        # 2. Sleek pointer cursor polygon
        cursor_poly = [
            (x, y),
            (x, y + 18),
            (x + 5, y + 14),
            (x + 10, y + 22),
            (x + 13, y + 20),
            (x + 8, y + 13),
            (x + 14, y + 13),
        ]
        # Dark outline for contrast
        draw.polygon(cursor_poly, fill=cursor_color, outline=(25, 10, 50, 220))

        # 3. Collaborative badge pill: [ 🤖 Gemini (x,y) ]
        badge_str = f"🤖 {label} ({x}, {y})"
        bx, by = x + 16, y + 16
        bw = max(90, len(badge_str) * 7 + 12)
        bh = 18
        draw.rounded_rectangle([(bx, by), (bx + bw, by + bh)], radius=4, fill=badge_bg)
        draw.text((bx + 6, by + 3), badge_str, fill=badge_text, font=font)

        result = Image.alpha_composite(base, overlay).convert("RGB")
        result.save(output_path, "PNG")

    return output_path


def _get_pixels(img: Image.Image) -> List[Any]:
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    return list(img.getdata())


def compare_screenshots(image_path_a: str, image_path_b: str, threshold: float = 0.005) -> Tuple[float, bool]:
    """Compare two screenshots to measure visual difference ratio."""
    with Image.open(image_path_a).convert("RGB") as img_a, Image.open(image_path_b).convert("RGB") as img_b:
        if img_a.size != img_b.size:
            return 1.0, True

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
    """Analyze basic visual metrics of the screenshot."""
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


def create_compact_thumbnail(
    image_path: str,
    max_dim: int = 512,
    quality: int = 55,
    output_path: Optional[str] = None,
) -> str:
    """Downscale and compress screenshot to minimize VLM vision token consumption.

    Images scaled under 512px occupy the minimum base token tier (~258 tokens instead of 2000+),
    saving 85-90% of token consumption per message.
    """
    if not output_path:
        root, _ = os.path.splitext(image_path)
        output_path = f"{root}_compact.jpg"

    with Image.open(image_path) as img:
        img_rgb = img.convert("RGB")
        w, h = img_rgb.size
        scale = min(1.0, max_dim / max(w, h))
        if scale < 1.0:
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            img_rgb = img_rgb.resize(new_size, Image.Resampling.BILINEAR)

        img_rgb.save(output_path, "JPEG", quality=quality, optimize=True)

    return output_path


def crop_region(
    image_path: str,
    bbox: Tuple[int, int, int, int],
    output_path: Optional[str] = None,
) -> str:
    """Crop a Region of Interest (ROI) [x1, y1, x2, y2] to avoid sending full-screen images."""
    if not output_path:
        root, _ = os.path.splitext(image_path)
        output_path = f"{root}_crop.png"

    with Image.open(image_path) as img:
        cropped = img.crop(bbox)
        cropped.save(output_path, "PNG")

    return output_path


def transcribe_screen(image_path: str) -> Dict[str, Any]:
    """Attempt OCR transcription if pytesseract is installed."""
    try:
        import pytesseract  # type: ignore
        text = pytesseract.image_to_string(Image.open(image_path))
        return {"available": True, "text": text.strip()}
    except ImportError:
        return {
            "available": False,
            "text": "",
            "note": "pytesseract not installed in host Python environment. Multimodal VLM inspection recommended.",
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}
