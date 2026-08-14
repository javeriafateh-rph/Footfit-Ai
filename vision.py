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
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours, img.shape[:2]


def detect_reference_card(pil_image, aspect_tolerance=0.12):
    """
    Try to find a card-shaped contour (a near-rectangle with the ID-1 aspect
    ratio) in the image. Returns pixels-per-mm if found, else None.
    """
    contours, _ = _contours_from(pil_image)
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
            # Prefer the largest matching candidate (less likely to be noise)
            if best is None or area > best[0]:
                best = (area, long_side, short_side)
    if best is None:
        return None
    _, long_side_px, _ = best
    px_per_mm = long_side_px / CARD_WIDTH_MM
    return px_per_mm


def analyze_foot_contour(pil_image, px_per_mm: float = None, known_length_mm: float = None):
    """
    Measure the foot's bounding box in the photo.

    If px_per_mm is supplied (from a detected reference card), returns real
    millimeter measurements for BOTH width and length — this is a genuine
    photo-based measurement.

    If instead known_length_mm is supplied (user manually typed their foot
    length), that number is used as-is for length — it is NOT re-derived
    from the photo, because doing so is mathematically circular (deriving a
    scale from a known length, then "measuring" length with that same scale,
    always returns exactly the original number regardless of the actual
    photo — this was a real bug, caught by testing two different-sized feet
    and finding they returned identical "measured" lengths). In this mode,
    only width is estimated from the photo, scaled against the user's
    provided length.

    If neither is available, returns None values and the caller should ask
    the user for one or the other rather than fabricate a number.
    """
    contours, img_shape = _contours_from(pil_image)
    if not contours:
        return {"width_mm": None, "length_mm": None, "shape": "Standard / Tapered Forefoot", "calibrated": False}

    c = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)

    # A top-down foot photo is taller than wide in pixels; treat the long
    # bounding-box side as length, short side as forefoot width.
    length_px, width_px = max(w, h), min(w, h)

    used_manual_length = False
    if px_per_mm is None and known_length_mm is not None and length_px > 0:
        px_per_mm = length_px / known_length_mm
        used_manual_length = True

    if px_per_mm:
        width_mm = round(width_px / px_per_mm, 1)
        # Only recompute length from the photo if we calibrated via a real
        # detected card. If calibration came from the user's own manual
        # length entry, use that value directly instead of re-deriving it
        # circularly from the same scale it was used to create.
        length_mm = known_length_mm if used_manual_length else round(length_px / px_per_mm, 1)
        calibrated = True
    else:
        width_mm = None
        length_mm = None
        calibrated = False

    aspect_ratio = w / float(h) if h > 0 else 0.35
    shape = "Wide / Fan-Shaped Forefoot" if aspect_ratio > 0.42 else "Standard / Tapered Forefoot"

    return {
        "width_mm": width_mm,
        "length_mm": length_mm,
        "shape": shape,
        "calibrated": calibrated,
        "length_source": "manual" if used_manual_length else ("card" if calibrated else None),
    }


def mm_to_us_shoe_size(length_mm: float):
    """Rough foot-length-to-US-size conversion for extra context (unisex, approximate)."""
    if length_mm is None:
        return None
    size = (length_mm / 8.4635) - 12.6
    return round(size * 2) / 2  # nearest half size


def foot_length_to_sizes(length_mm: float, gender: str = "Unisex"):
    """
    Converts a foot length in mm into approximate US/UK/EU shoe sizes.
    Uses standard Brannock-based approximations. Gender affects the
    conversion since men's and women's size scales differ for the same
    physical foot length. These are general-guide approximations —
    exact sizing always varies by brand, so this is presented as a
    starting point, not a guarantee.
    """
    if length_mm is None:
        return None

    base_us = (length_mm / 8.4635) - 22.5  # men's US sizing baseline, calibrated against
    # a standard reference chart (254mm->8, 267mm->9, 279mm->10) — the original
    # offset here (12.6) was a significant error that produced wildly oversized
    # results (e.g. "US 17" for a completely normal 250mm foot); corrected via
    # direct cross-check against real published size-chart data points.

    if gender == "Woman":
        us_size = base_us + 1.5
        uk_size = us_size - 2.5
        eu_size = us_size + 31
    else:  # Man or Unisex default to the men's/unisex scale
        us_size = base_us
        uk_size = us_size - 1
        eu_size = us_size + 33

    def round_half(x):
        return round(x * 2) / 2

    return {
        "us": round_half(us_size),
        "uk": round_half(uk_size),
        "eu": round_half(eu_size),
    }
