"""
vision.py - Reliable vision detection for FootFit AI
"""

import cv2
import numpy as np

CARD_WIDTH_MM = 85.60
CARD_ASPECT = CARD_WIDTH_MM / 53.98


def detect_reference_card(pil_image):
    """
    Returns (px_per_mm, card_found_boolean) safely so app.py unpacking never crashes.
    """
    if pil_image is None:
        return None, False

    img_rgb = np.array(pil_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2RGB)
    h, w = img_bgr.shape[:2]
    img_area = h * w

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Color thresholding + adaptive edge fallback
    lower_blue = np.array([85, 40, 40])
    upper_blue = np.array([135, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_card = None
    for c in contours:
        area = cv2.contourArea(c)
        if area < (img_area * 0.003) or area > (img_area * 0.25):
            continue

        rect = cv2.minAreaRect(c)
        (rw, rh) = rect[1]
        if rw == 0 or rh == 0:
            continue

        long_side, short_side = max(rw, rh), min(rw, rh)
        ratio = long_side / short_side

        if abs(ratio - CARD_ASPECT) / CARD_ASPECT <= 0.35:
            if best_card is None or area > best_card[1]:
                best_card = (long_side, area)

    if best_card:
        px_per_mm = best_card[0] / CARD_WIDTH_MM
        return px_per_mm, True

    return None, False


def annotate_detection(pil_image, px_per_mm=None, known_length_mm=None):
    """Returns an RGB image with the reference card (green) and foot contour (blue) outlined."""
    img_rgb = np.array(pil_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    h, w = img_bgr.shape[:2]
    img_area = h * w

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    lower_blue = np.array([85, 40, 40])
    upper_blue = np.array([135, 255, 255])
    card_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    card_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    card_mask = cv2.morphologyEx(card_mask, cv2.MORPH_CLOSE, card_kernel)

    card_contours, _ = cv2.findContours(card_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_card, best_area = None, 0
    for c in card_contours:
        area = cv2.contourArea(c)
        if area < (img_area * 0.003) or area > (img_area * 0.25):
            continue
        rect = cv2.minAreaRect(c)
        (rw, rh) = rect[1]
        if rw == 0 or rh == 0:
            continue
        long_side, short_side = max(rw, rh), min(rw, rh)
        ratio = long_side / short_side
        if abs(ratio - CARD_ASPECT) / CARD_ASPECT <= 0.35 and area > best_area:
            best_card, best_area = rect, area

    if best_card is not None:
        box = cv2.boxPoints(best_card).astype(int)
        cv2.drawContours(img_bgr, [box], 0, (0, 255, 0), 3)

    lower_skin = np.array([0, 20, 60])
    upper_skin = np.array([25, 255, 255])
    skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
    skin_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, skin_kernel)

    foot_contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if foot_contours:
        foot_c = max(foot_contours, key=cv2.contourArea)
        cv2.drawContours(img_bgr, [foot_c], -1, (255, 0, 0), 3)

    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def analyze_foot_contour(pil_image, px_per_mm=None, known_length_mm=None):
    """Processes foot dimensions without raising AttributeError."""
    if pil_image is None:
        return {"width_mm": None, "length_mm": None, "shape": "Standard", "calibrated": False}

    img_rgb = np.array(pil_image.convert("RGB"))
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2RGB)

    # Skin color threshold
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lower_skin = np.array([0, 20, 60])
    upper_skin = np.array([25, 255, 255])
    skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return {"width_mm": None, "length_mm": None, "shape": "Standard", "calibrated": False}

    foot_c = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(foot_c)
    (rw, rh) = rect[1]
    length_px, width_px = max(rw, rh), min(rw, rh)

    if px_per_mm and px_per_mm > 0:
        width_mm = round(width_px / px_per_mm, 1)
        length_mm = round(length_px / px_per_mm, 1)
        calibrated = True
    elif known_length_mm and known_length_mm > 0:
        length_mm = known_length_mm
        width_mm = round((width_px / length_px) * known_length_mm, 1) if length_px > 0 else 95.0
        calibrated = True
    else:
        width_mm, length_mm, calibrated = None, None, False

    return {
        "width_mm": width_mm,
        "length_mm": length_mm,
        "shape": "Wide" if (width_px / (length_px or 1)) > 0.42 else "Standard",
        "calibrated": calibrated,
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
