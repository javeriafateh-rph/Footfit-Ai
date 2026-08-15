"""
vision.py
Foot photo analysis with robust card detection and bulletproof sizing math.
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
    
    # Adaptive thresholding to handle textured backgrounds (like marble)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 19, 3
    )
    
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    return contours, img.shape[:2]


def _find_card_contour(contours, image_area, aspect_tolerance=0.18):
    """
    Filters contours specifically for a credit card, excluding small floor patterns or huge background objects.
    """
    best = None
    for c in contours:
        area = cv2.contourArea(c)
        
        # A credit card in frame should be at least 0.5% and max 15% of the total image area
        if area < (image_area * 0.005) or area > (image_area * 0.15):
            continue
            
        rect = cv2.minAreaRect(c)
        (rw, rh) = rect[1]
        if rw == 0 or rh == 0:
            continue
            
        long_side, short_side = max(rw, rh), min(rw, rh)
        ratio = long_side / short_side
        
        # Check aspect ratio match against ~1.586
        if abs(ratio - CARD_ASPECT) / CARD_ASPECT <= aspect_tolerance:
            if best is None or area > best[3]:
                best = (c, long_side, short_side, area)
    return best


def detect_reference_card(pil_image, aspect_tolerance=0.18):
    """Try to find a card-shaped contour in the image. Returns pixels-per-mm if found, else None."""
    contours, (h, w) = _contours_from(pil_image)
    image_area = h * w
    card = _find_card_contour(contours, image_area, aspect_tolerance)
    if card is None:
        return None
    _, long_side_px, _, _ = card
    return long_side_px / CARD_WIDTH_MM


def analyze_foot_contour(
    pil_image, px_per_mm: float = None, known_length_mm: float = None
):
    """Measure the foot's bounding box in the photo."""
    contours, (h, w) = _contours_from(pil_image)
    image_area = h * w
    
    if not contours:
        return {
            "width_mm": None,
            "length_mm": None,
            "shape": "Standard / Tapered Forefoot",
            "calibrated": False,
            "length_source": None,
        }

    card = _find_card_contour(contours, image_area)
    card_contour = card[0] if card else None

    # Filter out card contour
    foot_candidates = [
        c for c in contours 
        if card_contour is None or not np.array_equal(c, card_contour)
    ]
    
    # Filter foot candidates to reasonably large objects (at least 2% of image)
    foot_candidates = [c for c in foot_candidates if cv2.contourArea(c) > (image_area * 0.02)]

    if not foot_candidates:
        return {
            "width_mm": None,
            "length_mm": None,
            "shape": "Standard / Tapered Forefoot",
            "calibrated": False,
            "length_source": None,
        }

    c = max(foot_candidates, key=cv2.contourArea)
    x, y, fw, fh = cv2.boundingRect(c)

    length_px, width_px = max(fw, fh), min(fw, fh)

    used_manual_length = False
    if px_per_mm is None and known_length_mm is not None and length_px > 0:
        if known_length_mm > 500:  # Fix double cm conversion
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

    aspect_ratio = fw / float(fh) if fh > 0 else 0.35
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

    contours, (h, w) = _contours_from(pil_image)
    image_area = h * w
    card = _find_card_contour(contours, image_area)
    
    if card:
        card_contour = card[0]
        cv2.drawContours(img, [card_contour], -1, (0, 200, 0), 3)
        cv2.putText(
            img, "CARD", tuple(card_contour[0][0]),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2
        )

    foot_candidates = [
        c for c in contours 
        if card is None or not np.array_equal(c, card[0])
    ]
    foot_candidates = [c for c in foot_candidates if cv2.contourArea(c) > (image_area * 0.02)]
    
    if foot_candidates:
        foot_contour = max(foot_candidates, key=cv2.contourArea)
        cv2.drawContours(img, [foot_contour], -1, (255, 100, 0), 3)
        x, y, fw, fh = cv2.boundingRect(foot_contour)
        cv2.putText(
            img, "FOOT", (x, max(y - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2
        )

    from PIL import Image as PILImage
    annotated_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return PILImage.fromarray(annotated_rgb)


def foot_length_to_sizes(length_mm: float, gender: str = "Unisex"):
    """
    Converts foot length in mm to realistic US/UK/EU sizes.
    """
    if length_mm is None or length_mm <= 0:
        return {"us": "-", "uk": "-", "eu": "-"}

    # Fix unit issues if length passed as cm instead of mm
    if length_mm < 50.0:
        length_mm = length_mm * 10.0

    length_cm = length_mm / 10.0

    # Standard Foot Length (cm) to EU Sizing: (Length + 1.5cm space) * 1.5
    eu_size = (length_cm + 1.5) * 1.5

    # Brannock Standard US Sizing Formula based on inches
    length_inches = length_cm / 2.54

    if gender == "Woman":
        us_size = (3 * length_inches) - 21.0
        uk_size = us_size - 2.0
    else:  # Man / Unisex
        us_size = (3 * length_inches) - 22.0
        uk_size = us_size - 1.0

    def round_half(x):
        return round(x * 2) / 2

    # Clamp bounds to valid positive shoe sizes
    final_us = max(1.0, min(16.0, round_half(us_size)))
    final_uk = max(0.5, min(15.0, round_half(uk_size)))
    final_eu = max(15.0, min(50.0, round_half(eu_size)))

    return {
        "us": final_us,
        "uk": final_uk,
        "eu": final_eu,
    }
