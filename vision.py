"""
vision.py
Foot photo analysis.

HONEST NOTE ON ACCURACY:
A single 2D photo can never give lab-grade measurements — there's no depth
information, and results depend on the phone's lens and how flat the foot
and camera are. What we CAN do reliably is give an accurate *relative*
measurement, by calibrating pixels-to-millimeters using an object of known,
fixed size in the same photo (a standard ID/credit/debit card: 85.60mm x
53.98mm — the ISO/IEC 7810 ID-1 size used worldwide). This turns "guessing
a plausible number" into "measuring against a ruler that happens to be a
card," which is the same trick many foot-sizing apps use.

If no card is detected, we fall back to asking the user for a known
foot length (e.g. from a ruler or a shoe insole) to calibrate instead.
Both paths are clearly labelled in the UI so the person knows which
measurement they're getting.
"""

import cv2
import numpy as np

# ISO/IEC 7810 ID-1 card size (credit card, driver's license, etc.)
CARD_WIDTH_MM = 85.60
CARD_HEIGHT_MM = 53.98
CARD_ASPECT = CARD_WIDTH_MM / CARD_HEIGHT_MM  # ~1.586


def _contours_from(pil_image):
    img_rgb = np.array(pil_image.convert("RGB"))
    img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    return contours, img.shape[:2]


def _find_card_contour(contours, aspect_tolerance=0.12):
    """Finds the best card-shaped contour among a set of contours."""
    best = None
    for c in contours:
        area = cv2.contourArea(c)
        if area < 500:
            continue
        rect = cv2.minAreaRect(c)
        (rw, rh) = rect[1]
        if rw == 0 or rh == 0:
            continue
        long_side, short_side = max(rw, rh), min(rw, rh)
        ratio = long_side / short_side
        if abs(ratio - CARD_ASPECT) / CARD_ASPECT <= aspect_tolerance:
            if best is None or area > best[3]:
                best = (c, long_side, short_side, area)
    return best


def detect_reference_card(pil_image, aspect_tolerance=0.12):
    """Try to find a card-shaped contour in the image. Returns pixels-per-mm if found, else None."""
    contours, _ = _contours_from(pil_image)
    card = _find_card_contour(contours, aspect_tolerance)
    if card is None:
        return None
    _, long_side_px, _, _ = card
    return long_side_px / CARD_WIDTH_MM


def analyze_foot_contour(
    pil_image, px_per_mm: float = None, known_length_mm: float = None
):
    """Measure the foot's bounding box in the photo."""
    contours, img_shape = _contours_from(pil_image)
    if not contours:
        return {
            "width_mm": None,
            "length_mm": None,
            "shape": "Standard / Tapered Forefoot",
            "calibrated": False,
            "length_source": None,
        }

    card = _find_card_contour(contours)
    card_contour = card[0] if card else None

    foot_candidates = [
        c
        for c in contours
        if card_contour is None or not np.array_equal(c, card_contour)
    ]
    if not foot_candidates:
        return {
            "width_mm": None,
            "length_mm": None,
            "shape": "Standard / Tapered Forefoot",
            "calibrated": False,
            "length_source": None,
        }

    c = max(foot_candidates, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)

    length_px, width_px = max(w, h), min(w, h)

    used_manual_length = False
    if px_per_mm is None and known_length_mm is not None and length_px > 0:
        # Sanity Guard: if user input known_length_mm > 500 (likely typed in cm multiplied mistakenly), auto-fix it
        if known_length_mm > 500:
            known_length_mm = known_length_mm / 10.0

        px_per_mm = length_px / known_length_mm
        used_manual_length = True

    if px_per_mm:
        width_mm = round(width_px / px_per_mm, 1)
        length_mm = (
            known_length_mm
            if used_manual_length
            else round(length_px / px_per_mm, 1)
        )
        calibrated = True
    else:
        width_mm = None
        length_mm = None
        calibrated = False

    aspect_ratio = w / float(h) if h > 0 else 0.35
    shape = (
        "Wide / Fan-Shaped Forefoot"
        if aspect_ratio > 0.42
        else "Standard / Tapered Forefoot"
    )

    return {
        "width_mm": width_mm,
        "length_mm": length_mm,
        "shape": shape,
        "calibrated": calibrated,
        "length_source": "manual"
        if used_manual_length
        else ("card" if calibrated else None),
    }


def annotate_detection(
    pil_image, px_per_mm: float = None, known_length_mm: float = None
):
    img_rgb = np.array(pil_image.convert("RGB")).copy()
    img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    contours, _ = _contours_from(pil_image)
    card = _find_card_contour(contours)
    if card:
        card_contour = card[0]
        cv2.drawContours(img, [card_contour], -1, (0, 200, 0), 3)
        cv2.putText(
            img,
            "CARD",
            tuple(card_contour[0][0]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 200, 0),
            2,
        )

    foot_candidates = [
        c for c in contours if card is None or not np.array_equal(c, card[0])
    ]
    if foot_candidates:
        foot_contour = max(foot_candidates, key=cv2.contourArea)
        cv2.drawContours(img, [foot_contour], -1, (255, 100, 0), 3)
        x, y, w, h = cv2.boundingRect(foot_contour)
        cv2.putText(
            img,
            "FOOT",
            (x, max(y - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 100, 0),
            2,
        )

    from PIL import Image as PILImage

    annotated_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return PILImage.fromarray(annotated_rgb)


def mm_to_us_shoe_size(length_mm: float):
    if length_mm is None:
        return None
    # Auto-fix unit if passed in cm instead of mm
    if length_mm < 50:
        length_mm = length_mm * 10.0
    size = (length_mm / 8.4635) - 22.5
    return round(max(1.0, size) * 2) / 2


def foot_length_to_sizes(length_mm: float, gender: str = "Unisex"):
    """Converts a foot length in mm into accurate US/UK/EU shoe sizes.

    Includes unit validation and bounds clamping.
    """
    if length_mm is None:
        return {"us": "-", "uk": "-", "eu": "-"}

    # --- UNIT SAFETY SANITY CHECK ---
    # Human feet are between 100mm (baby) and 350mm (giant adult).
    # If length_mm > 500, the user likely passed mm derived from an oversized cm value.
    if length_mm > 500.0:
        length_mm = length_mm / 10.0  # Convert back to actual mm

    # If length_mm is < 50, user passed cm instead of mm
    if length_mm < 50.0:
        length_mm = length_mm * 10.0

    # Standard Brannock Men's Baseline: (length_mm / 8.4635) - 22.5
    # (e.g. 254mm = 25.4cm -> US 7.5 / 8.0)
    base_us = (length_mm / 8.4635) - 22.5

    if gender == "Woman":
        us_size = base_us + 1.5
        uk_size = us_size - 2.0
        eu_size = (length_mm / 10.0 + 1.5) * 1.5
    else:  # Man or Unisex
        us_size = base_us
        uk_size = us_size - 1.0
        eu_size = (length_mm / 10.0 + 1.5) * 1.5

    def round_half(x):
        return round(x * 2) / 2

    # Clamp sizes to realistic human ranges
    final_us = max(1.0, min(20.0, round_half(us_size)))
    final_uk = max(0.5, min(19.5, round_half(uk_size)))
    final_eu = max(15.0, min(55.0, round_half(eu_size)))

    return {
        "us": final_us,
        "uk": final_uk,
        "eu": final_eu,
    }
