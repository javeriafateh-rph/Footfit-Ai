"""
vision.py
Foot photo analysis with enhanced card detection for patterned surfaces.
"""

import cv2
import numpy as np

CARD_WIDTH_MM = 85.60
CARD_HEIGHT_MM = 53.98
CARD_ASPECT = CARD_WIDTH_MM / CARD_HEIGHT_MM  # ~1.586


def _contours_from_image(pil_image):
    """Generates multiple binary masks (adaptive + color/saturation) to catch cards on marble/patterned floors."""
    img_rgb = np.array(pil_image.convert("RGB"))
    img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Blur to remove fine marble tile noise
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # Mask 1: Otsu Thresholding
    _, thresh1 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Mask 2: Adaptive Thresholding (handles non-uniform indoor lighting)
    thresh2 = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5
    )

    # Mask 3: Saturation-based isolation (Cards usually have strong colors compared to grey/white marble)
    sat = hsv[:, :, 1]
    _, thresh3 = cv2.threshold(sat, 40, 255, cv2.THRESH_BINARY)

    combined_thresh = cv2.bitwise_or(thresh1, thresh3)

    contours, _ = cv2.findContours(combined_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours, img.shape[:2], img


def _find_card_contour(contours, img_shape, aspect_tolerance=0.20):
    """Filters contours to locate a standard ID/credit card contour."""
    h, w = img_shape
    img_area = h * w
    best = None

    for c in contours:
        area = cv2.contourArea(c)
        # Card must occupy between 0.3% and 12% of total image frame
        if area < (img_area * 0.003) or area > (img_area * 0.12):
            continue

        rect = cv2.minAreaRect(c)
        (rw, rh) = rect[1]
        if rw == 0 or rh == 0:
            continue

        long_side, short_side = max(rw, rh), min(rw, rh)
        ratio = long_side / short_side

        # Match against standard card aspect ratio (~1.586)
        if abs(ratio - CARD_ASPECT) / CARD_ASPECT <= aspect_tolerance:
            if best is None or area > best[3]:
                best = (c, long_side, short_side, area)

    return best


def detect_reference_card(pil_image, aspect_tolerance=0.20):
    """Detects card contour and returns pixels per millimeter."""
    contours, img_shape, _ = _contours_from_image(pil_image)
    card = _find_card_contour(contours, img_shape, aspect_tolerance)
    if card is None:
        return None
    _, long_side_px, _, _ = card
    return long_side_px / CARD_WIDTH_MM


def analyze_foot_contour(pil_image, px_per_mm: float = None, known_length_mm: float = None):
    """Extracts foot length/width in mm."""
    contours, img_shape, img = _contours_from_image(pil_image)
    h, w = img_shape
    img_area = h * w

    if not contours:
        return {"width_mm": None, "length_mm": None, "shape": "Standard", "calibrated": False, "length_source": None}

    card = _find_card_contour(contours, img_shape)
    card_contour = card[0] if card else None

    # Exclude card contour from foot consideration
    candidates = [c for c in contours if card_contour is None or not np.array_equal(c, card_contour)]
    
    # Foot contour must be larger than a card (at least 2.5% of total frame)
    candidates = [c for c in candidates if cv2.contourArea(c) > (img_area * 0.025)]

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
    """Outlines detected card in green and foot in blue."""
    contours, img_shape, img = _contours_from_image(pil_image)
    h, w = img_shape
    img_area = h * w

    card = _find_card_contour(contours, img_shape)
    if card:
        cv2.drawContours(img, [card[0]], -1, (0, 255, 0), 3)
        cv2.putText(img, "CARD DETECTED", tuple(card[0][0][0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    candidates = [c for c in contours if card is None or not np.array_equal(c, card[0])]
    candidates = [c for c in candidates if cv2.contourArea(c) > (img_area * 0.025)]

    if candidates:
        foot_c = max(candidates, key=cv2.contourArea)
        cv2.drawContours(img, [foot_c], -1, (255, 0, 0), 3)
        x, y, fw, fh = cv2.boundingRect(foot_c)
        cv2.putText(img, "FOOT DETECTED", (x, max(y - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

    from PIL import Image as PILImage
    return PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def foot_length_to_sizes(length_mm: float, gender: str = "Unisex"):
    """Calculates US/UK/EU shoe sizes from foot length in mm."""
    if length_mm is None or length_mm <= 0:
        return {"us": "-", "uk": "-", "eu": "-"}

    if length_mm < 50.0:
        length_mm = length_mm * 10.0

    length_cm = length_mm / 10.0

    # International EU size formula: (Length in cm + 1.5 cm toe clearance) * 1.5
    eu_size = (length_cm + 1.5) * 1.5

    # Brannock US size conversion based on inches
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
