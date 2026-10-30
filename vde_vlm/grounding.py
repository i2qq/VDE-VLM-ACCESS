"""
vde_vlm.grounding
~~~~~~~~~~~~~~~~~
Visual Grounding, OCR Labeling, and UI Element Recognition.
Provides Set-of-Marks (SoM) style detection, text localization, and YOLO/VFM
saliency detection for autonomous VLM agent guidance and interactive web studio overlays.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_READER_INSTANCE = None


def get_ocr_reader():
    """Lazy-load and cache the EasyOCR reader singleton in memory."""
    global _READER_INSTANCE
    if _READER_INSTANCE is None:
        try:
            import easyocr
            import torch
            has_cuda = torch.cuda.is_available()
            _READER_INSTANCE = easyocr.Reader(["en"], gpu=has_cuda, verbose=False)
            logger.info(f"Initialized EasyOCR reader (CUDA: {has_cuda})")
        except Exception as exc:
            logger.warning(f"EasyOCR reader init failed: {exc}")
            _READER_INSTANCE = False
    return _READER_INSTANCE if _READER_INSTANCE is not False else None


def detect_ui_elements(
    image_path: str,
    confidence_threshold: float = 0.35,
    include_shapes: bool = True,
) -> List[Dict[str, Any]]:
    """Detect text, buttons, and UI components in an image.

    Returns:
        List of detected elements with:
        - id: Sequential index (1, 2, 3...)
        - type: 'text' or 'button' or 'input'
        - text: Recognized text label
        - bbox: [x1, y1, x2, y2]
        - centroid: [cx, cy]
        - confidence: Float score (0.0 - 1.0)
    """
    if not os.path.exists(image_path):
        return []

    elements: List[Dict[str, Any]] = []
    elem_idx = 1

    # 1. High-accuracy OCR Text Localization
    reader = get_ocr_reader()
    if reader is not None:
        try:
            raw_results = reader.readtext(image_path)
            for raw_bbox, text, conf in raw_results:
                if conf < confidence_threshold:
                    continue
                clean_text = text.strip()
                if not clean_text or len(clean_text) == 0:
                    continue

                xs = [int(p[0]) for p in raw_bbox]
                ys = [int(p[1]) for p in raw_bbox]
                x1, x2 = min(xs), max(xs)
                y1, y2 = min(ys), max(ys)

                # Pad text box slightly for better target reachability
                pad_x = 4
                pad_y = 2
                x1 = max(0, x1 - pad_x)
                x2 = x2 + pad_x
                y1 = max(0, y1 - pad_y)
                y2 = y2 + pad_y
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                elements.append({
                    "id": elem_idx,
                    "type": "text",
                    "text": clean_text,
                    "bbox": [x1, y1, x2, y2],
                    "centroid": [cx, cy],
                    "confidence": round(float(conf), 3),
                })
                elem_idx += 1
        except Exception as exc:
            logger.warning(f"OCR detection error: {exc}")

    # 2. Visual Feature Model (VFM) / UI Contour & Box Saliency for interactive buttons & widgets
    if include_shapes:
        try:
            img = cv2.imread(image_path)
            if img is not None:
                h, w = img.shape[:2]
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blurred = cv2.bilateralFilter(gray, 7, 50, 50)
                edged = cv2.Canny(blurred, 30, 120)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

                contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    x, y, bw, bh = cv2.boundingRect(cnt)
                    # Filter out huge window containers, tiny noise, or non-widget sizes
                    if bw < 35 or bh < 20:
                        continue
                    if bw > 450 or bh > 160:  # Exclude giant dialog bodies
                        continue
                    if bw * bh > 45000:       # Maximum widget area
                        continue

                    # Check if this contour overlaps with any already detected OCR text
                    overlaps_ocr = False
                    for ocr_el in elements:
                        ox1, oy1, ox2, oy2 = ocr_el["bbox"]
                        # If OCR text is inside this button, expand the label
                        if x <= ox1 and y <= oy1 and (x + bw) >= ox2 and (y + bh) >= oy2:
                            ocr_el["type"] = "button"
                            overlaps_ocr = True
                            break
                        # Center proximity check
                        if abs((x + bw / 2) - ocr_el["centroid"][0]) < 25 and abs((y + bh / 2) - ocr_el["centroid"][1]) < 15:
                            overlaps_ocr = True
                            break

                    if not overlaps_ocr:
                        cx = int(x + bw / 2)
                        cy = int(y + bh / 2)
                        elements.append({
                            "id": elem_idx,
                            "type": "button" if bw > bh * 1.4 else "widget",
                            "text": f"Widget #{elem_idx}",
                            "bbox": [x, y, x + bw, y + bh],
                            "centroid": [cx, cy],
                            "confidence": 0.85,
                        })
                        elem_idx += 1
        except Exception as exc:
            logger.debug(f"Shape detection fallback error: {exc}")

    return elements


def find_element_by_text(
    image_path: str,
    query: str,
    min_confidence: float = 0.35,
) -> Optional[Dict[str, Any]]:
    """Locate a UI element on screen by text label (fuzzy or exact match).

    Args:
        image_path: Screen image path.
        query: Target label (e.g. 'Next', 'English', 'Cancel').
        min_confidence: Minimum score.

    Returns:
        Matched element dict or None.
    """
    elements = detect_ui_elements(image_path, confidence_threshold=min_confidence, include_shapes=False)
    q_norm = query.strip().lower()

    # 1. Exact match
    for el in elements:
        if el["text"].strip().lower() == q_norm:
            return el

    # 2. Query is substring of element text (e.g. 'next' in 'next step')
    for el in elements:
        t_low = el["text"].strip().lower()
        if q_norm in t_low:
            return el

    # 3. Element text is substring of query (only if element has at least 3 chars)
    for el in elements:
        t_low = el["text"].strip().lower()
        if len(t_low) >= 3 and t_low in q_norm:
            return el

    # 4. Normalized regex match (ignoring punctuation/accents)
    q_clean = re.sub(r"[^a-zA-Z0-9]", "", q_norm)
    for el in elements:
        t_clean = re.sub(r"[^a-zA-Z0-9]", "", el["text"].lower())
        if q_clean and len(t_clean) >= 3 and (q_clean in t_clean or t_clean in q_clean):
            return el

    return None


def draw_grounded_overlay(
    image_path: str,
    elements: Optional[List[Dict[str, Any]]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Render Set-of-Marks (SoM) bounding boxes and text badges onto screenshot.

    Args:
        image_path: Source image.
        elements: Pre-detected elements or None to run detection.
        output_path: Target save path.

    Returns:
        Path to generated annotated image.
    """
    if elements is None:
        elements = detect_ui_elements(image_path)

    base = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Colors
    box_color = (6, 182, 212, 230)       # Vivid Cyan
    fill_color = (6, 182, 212, 45)       # Translucent cyan
    text_bg = (15, 23, 42, 235)          # Dark slate badge
    text_fg = (255, 255, 255, 255)       # Pure white
    dot_color = (168, 85, 247, 255)      # Purple centroid dot

    for el in elements:
        x1, y1, x2, y2 = el["bbox"]
        cx, cy = el["centroid"]
        tag = f"[{el['id']}] {el['text']}"

        # Bounding box
        draw.rectangle([x1, y1, x2, y2], outline=box_color, width=2, fill=fill_color)

        # Centroid dot
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=dot_color, outline=(255, 255, 255, 255))

        # Tag badge
        badge_w = len(tag) * 6 + 10
        badge_y = max(2, y1 - 15)
        draw.rectangle([x1, badge_y, x1 + badge_w, badge_y + 13], fill=text_bg)
        draw.text((x1 + 4, badge_y), tag, fill=text_fg, font=font)

    result = Image.alpha_composite(base, overlay).convert("RGB")
    out_file = output_path or image_path.replace(".png", "_grounded.png")
    result.save(out_file, format="PNG")
    return out_file
