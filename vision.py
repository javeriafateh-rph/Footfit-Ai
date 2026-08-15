"""
vision.py - Robust Foot and Card Detection Pipeline
"""

import cv2
import numpy as np

CARD_WIDTH_MM = 85.60
CARD_HEIGHT_MM = 53.98
CARD_ASPECT = CARD_WIDTH_MM / CARD_HEIGHT_MM  # ~1.586


def isolate_card_and_foot(img_bgr):
    """Segment foot (skin tone) and card (blue/dark object) using HSV color space."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # 1. Skin Color Mask (Foot)
    lower_skin = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin = np.array([20, 255, 255], dtype=np.uint8)
    skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

    # Clean skin mask noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

    # 2. Blue Card Mask (Card)
    lower_blue = np.array([90, 50, 50], dtype=np.uint8)
    upper_blue = np.array([130, 255, 255], dtype=np.uint8)
    card_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    card_mask = cv2.morphologyEx(card_mask, cv2.MORPH_CLOSE, kernel)

    return skin_mask, card_mask


def _find_card_contour(card_mask, img_shape):
    """Find vertical or horizontal card contours cleanly."""
    contours, _ = cv2.findContours(card_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = img_shape
    img_area = h * w
    best = None

    for c in contours:
        area = cv2.contourArea(c)
        if area < (img_area * 0.005) or area > (img_area * 0.25):
            continue

        rect = cv2.minAreaRect(c)
        (rw, rh) = rect[1]
        if rw == 0 or rh == 0:
            continue

        long_side, short_side = max(rw, rh), min(rw, rh)
        ratio = long_side / short_side

        # Check aspect ratio tolerance regardless of vertical/horizontal orientation
        if abs(ratio - CARD_ASPECT) / CARD_ASPECT <= 0.30:
            if best is None or area > best[3]:
                best = (c, long_side, short_side, area)

    return best


def analyze_foot_contour(pil_image, px_per_mm: float = None, known_length_mm: float = None):
    img_rgb = np.array(pil_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    h, w = img_bgr.shape[:2]

    skin_mask, card_mask = isolate_card_and_foot(img_bgr)

    # Detect Card
    card = _find_card_contour(card_mask, (h, w))
    if card and px_per_mm is None:
        long_side_px = card[1]
        px_per_mm = long_side_px / CARD_WIDTH_MM

    # Detect Foot
    foot_contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not foot_contours:
        return {"width_mm": None, "length_mm": None, "shape": "Standard", "calibrated": False}

    # Select largest contiguous skin contour
    foot_c = max(foot_contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(foot_c)
    (rw, rh) = rect[1]
    length_px, width_px = max(rw, rh), min(rw, rh)

    if px_per_mm:
        width_mm = round(width_px / px_per_mm, 1)
        length_mm = round(length_px / px_per_mm, 1)
        calibrated = True
    else:
        width_mm, length_mm, calibrated = None, None, False

    return {
        "width_mm": width_mm,
        "length_mm": length_mm,
        "shape": "Wide" if (width_px / (length_px or 1)) > 0.42 else "Standard",
        "calibrated": calibrated,
    }
