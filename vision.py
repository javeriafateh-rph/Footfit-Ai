"""
vision.py
Foot photo analysis with HSV color targeting & morphological closing.
"""

import cv2
import numpy as np

CARD_WIDTH_MM = 85.60
CARD_HEIGHT_MM = 53.98
CARD_ASPECT = CARD_WIDTH_MM / CARD_HEIGHT_MM  # ~1.586


def _get_card_mask(img_bgr):
    """
    Combines edge thresholding AND color isolation (green/cyan/blue cards)
    so cards on marble floors stand out clearly.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # 1. Adaptive Thresholding
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 3
    )

    # 2. Color Range for Green/Cyan/Teal/Blue Debit Cards
    lower_color = np.array([35, 30, 30])
    upper_color = np.array([140, 255, 255])
    color_mask = cv2.inRange(hsv, lower_color, upper_color)

    # Combine both strategies
    combined = cv2.bitwise_or(thresh, color_mask)

    # 3. Morphological Closing (Bridge the gap caused by the black magnetic stripe)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

    return closed


def _contours_from_image(pil_image):
    img_rgb = np.array(pil_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    mask = _get_card_mask(img_bgr)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours, img_bgr.shape[:2], img_bgr


def _find_card_contour(contours, img_shape, aspect_tolerance=0.35):
    """
    Locates the credit card contour using flexible aspect tolerance to account for camera angles.
    """
    h, w = img_shape
    img_area = h * w
    best = None

    for c in contours:
        area = cv2.contourArea(c)
        # Card must occupy between 0.2% and 20% of the image frame
        if area < (img_area * 0.002) or area > (img_area * 0.20):
            continue

        rect = cv2.minAreaRect(c)
        (rw, rh) = rect[1]
        if rw == 0 or rh == 0:
            continue

        long_side, short_side = max(rw, rh), min(rw, rh)
        ratio = long_side / short_side

        # Wider tolerance (0.35) handles top-down photos taken at slight angles
        if abs(ratio - CARD_ASPECT) / CARD_ASPECT <= aspect_tolerance:
            if best is None or area > best[3]:
                best = (c, long_side, short_side, area)

    return best


def detect_reference_card(pil_image, aspect_tolerance=0.35):
    contours, img_shape, _ = _contours_from_image(pil_image)
    card = _find_card_contour(contours, img_shape, aspect_tolerance)
    if card is None:
        return None
    _, long_side_px, _, _ = card
    return long_side_px / CARD_WIDTH_MM


def analyze_foot_contour(pil_image, px_per_mm: float = None, known_length_mm: float = None):
    contours, img_shape, _ = _contours_from_image(pil_image)
    h, w = img_shape
    img_area = h * w

    if not contours:
        return {"width_mm": None, "length_mm": None, "shape": "Standard", "calibrated": False, "length_source": None}

    card = _find_card_contour(contours, img_shape)
    card_contour = card[0] if card else None

    # Exclude card contour from foot selection
    candidates = [c for c in contours if card_contour is None or not np.array_equal(c, card_contour)]
    candidates = [c for c in candidates if cv2.contourArea(c) > (img_area * 0.015)]

    if not candidates:
        return {"width_mm": None, "length_mm": None, "shape": "Standard", "calibrated": False, "length_source": None}

    foot_c = max(candidates, key=cv2.contourArea)
    rect = cv2.minAreaRect(foot_c)
    (rw, rh) = rect[1]
    length_px, width_px = max(rw, rh), min(rw, rh)

    used_manual = False
    if px_per_mm is None and known_length_mm is not None and length_px > 0:
        if known_length_mm > 500:
            known_length_mm = known_length_mm / 10.0
        px_per_mm = length_px / known_length_mm
        used_manual = True

    if px_per_mm:
        width_mm = round(width_px / px_per_mm, 1)
        length_mm = known_length_mm if used_manual else round(length_px / px_per_mm, 1)
        calibrated = True
    else:
        width_mm = None
        length_mm = None
        calibrated = False

    aspect_ratio = width_px / float(length_px) if length_px > 0 else 0.35
    shape = "Wide / Fan-Shaped Forefoot" if aspect_ratio > 0.42 else "Standard / Tapered Forefoot"

    return {
        "width_mm": width_mm,
        "length_mm": length_mm,
        "shape": shape,
        "calibrated": calibrated,
        "length_source": "manual" if used_manual else ("card" if calibrated else None),
    }


def annotate_detection(pil_image, px_per_mm: float = None, known_length_mm: float = None):
    contours, img_shape, img_bgr = _contours_from_image(pil_image)
    h, w = img_shape
    img_area = h * w

    card = _find_card_contour(contours, img_shape)
    if card:
        cv2.drawContours(img_bgr, [card[0]], -1, (0, 255, 0), 3)
        cv2.putText(img_bgr, "CARD DETECTED", tuple(card[0][0][0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    candidates = [c for c in contours if card is None or not np.array_equal(c, card[0])]
    candidates = [c for c in candidates if cv2.contourArea(c) > (img_area * 0.015)]

    if candidates:
        foot_c = max(candidates, key=cv2.contourArea)
        cv2.drawContours(img_bgr, [foot_c], -1, (255, 0, 0), 3)
        x, y, fw, fh = cv2.boundingRect(foot_c)
        cv2.putText(img_bgr, "FOOT DETECTED", (x, max(y - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

    from PIL import Image as PILImage
    return PILImage.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))


def foot_length_to_sizes(length_mm: float, gender: str = "Unisex"):
    if length_mm is None or length_mm <= 0:
        return {"us": "-", "uk": "-", "eu": "-"}

    if length_mm < 50.0:
        length_mm = length_mm * 10.0

    length_cm = length_mm / 10.0
    eu_size = (length_cm + 1.5) * 1.5
    length_inches = length_cm / 2.54

    if gender == "Woman":
        us_size = (3 * length_inches) - 21.0
        uk_size = us_size - 2.0
    else:
        us_size = (3 * length_inches) - 22.0
        uk_size = us_size - 1.0

    def round_half(x):
        return round(x * 2) / 2

    return {
        "us": max(1.0, min(16.0, round_half(us_size))),
        "uk": max(0.5, min(15.0, round_half(uk_size))),
        "eu": max(15.0, min(50.0, round_half(eu_size))),
    }
