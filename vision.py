"""
vision.py - Reliable vision detection for FootFit AI
"""

import cv2
import numpy as np

CARD_WIDTH_MM = 85.60
CARD_ASPECT = CARD_WIDTH_MM / 53.98


def _find_card_rect(img_bgr):
    """Locates the best card-shaped rectangle by edges + aspect ratio (color-agnostic).

    A pure color mask only finds cards that happen to match one hue, so most
    real ID/credit cards (white, gray, black, patterned) were never detected.
    Detecting by shape instead works regardless of the card's color.
    """
    h, w = img_bgr.shape[:2]
    img_area = h * w

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=2)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    best_rect, best_deviation = None, None
    for c in contours:
        area = cv2.contourArea(c)
        if area < (img_area * 0.003) or area > (img_area * 0.25):
            continue

        rect = cv2.minAreaRect(c)
        (rw, rh) = rect[1]
        if rw == 0 or rh == 0:
            continue

        # A real card is a solid rectangle that nearly fills its bounding box.
        # Irregular shapes (limbs, merged background texture) that coincidentally
        # have a card-like aspect ratio tend to fill much less of their box, so
        # this rejects them even when their aspect ratio alone would pass.
        extent = area / (rw * rh)
        if extent < 0.6:
            continue

        long_side, short_side = max(rw, rh), min(rw, rh)
        ratio = long_side / short_side
        deviation = abs(ratio - CARD_ASPECT) / CARD_ASPECT

        if deviation <= 0.15 and (best_deviation is None or deviation < best_deviation):
            best_rect, best_deviation = rect, deviation

    return best_rect


def _find_foot_contour(img_bgr):
    """Returns the largest skin-toned contour, or None if no foot-like region is found.

    On a warm-toned background (tan/brown rugs, wood floors) the skin-color mask
    can match most of the frame, merging the foot with the background into one
    giant blob. A real foot photographed reasonably close-up occupies a bounded
    portion of the frame, so an implausibly large match is rejected as unreliable
    rather than returned as a bogus measurement.
    """
    h, w = img_bgr.shape[:2]
    img_area = h * w

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lower_skin = np.array([0, 20, 60])
    upper_skin = np.array([25, 255, 255])
    skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    foot_c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(foot_c) > (img_area * 0.35):
        return None
    return foot_c


def detect_reference_card(pil_image):
    """
    Returns (px_per_mm, card_found_boolean) safely so app.py unpacking never crashes.
    """
    if pil_image is None:
        return None, False

    img_rgb = np.array(pil_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    rect = _find_card_rect(img_bgr)
    if rect is None:
        return None, False

    (rw, rh) = rect[1]
    long_side = max(rw, rh)
    px_per_mm = long_side / CARD_WIDTH_MM
    return px_per_mm, True


def annotate_detection(pil_image, px_per_mm=None, known_length_mm=None):
    """Returns an RGB image with the reference card (green) and foot contour (blue) outlined."""
    img_rgb = np.array(pil_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    card_rect = _find_card_rect(img_bgr)
    if card_rect is not None:
        box = cv2.boxPoints(card_rect).astype(int)
        cv2.drawContours(img_bgr, [box], 0, (0, 255, 0), 3)

    foot_c = _find_foot_contour(img_bgr)
    if foot_c is not None:
        cv2.drawContours(img_bgr, [foot_c], -1, (255, 0, 0), 3)

    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def analyze_foot_contour(pil_image, px_per_mm=None, known_length_mm=None):
    """Processes foot dimensions without raising AttributeError."""
    if pil_image is None:
        return {"width_mm": None, "length_mm": None, "shape": "Standard", "calibrated": False}

    img_rgb = np.array(pil_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    foot_c = _find_foot_contour(img_bgr)
    if foot_c is None:
        return {"width_mm": None, "length_mm": None, "shape": "Standard", "calibrated": False}

    rect = cv2.minAreaRect(foot_c)
    (rw, rh) = rect[1]
    length_px, width_px = max(rw, rh), min(rw, rh)

    if px_per_mm and px_per_mm > 0:
        width_mm = round(width_px / px_per_mm, 1)
        length_mm = round(length_px / px_per_mm, 1)
        calibrated = True
        length_source = "card"
    elif known_length_mm and known_length_mm > 0:
        length_mm = known_length_mm
        width_mm = round((width_px / length_px) * known_length_mm, 1) if length_px > 0 else 95.0
        calibrated = True
        length_source = "manual"
    else:
        width_mm, length_mm, calibrated = None, None, False
        length_source = None

    return {
        "width_mm": width_mm,
        "length_mm": length_mm,
        "shape": "Wide" if (width_px / (length_px or 1)) > 0.42 else "Standard",
        "calibrated": calibrated,
        "length_source": length_source,
    }


def foot_length_to_sizes(length_mm: float, gender: str = "Unisex"):
    if not length_mm or length_mm <= 0:
        return {"us": "-", "uk": "-", "eu": "-"}

    length_cm = length_mm / 10.0 if length_mm > 50 else length_mm
    eu_size = round(((length_cm + 1.5) * 1.5) * 2) / 2
    length_inches = length_cm / 2.54

    us_offset = 21.0 if gender == "Woman" else 22.0
    us_size = round(((3 * length_inches) - us_offset) * 2) / 2
    uk_size = us_size - (2.0 if gender == "Woman" else 1.0)

    return {"us": max(1.0, us_size), "uk": max(0.5, uk_size), "eu": max(15.0, eu_size)}
