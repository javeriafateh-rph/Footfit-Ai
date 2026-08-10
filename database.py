"""
database.py — v2

What changed from v1:
- Added `category` (Everyday / Sports & Training / Medical & Comfort)
- Added `toe_box_shape` (Round / Pointed / Square / Wide-Anatomical) — a shoe
  attribute, distinct from the wearer's toe shape (handled in matching.py)
- Added `width` (Narrow / Standard / Wide / Extra Wide)
- Prices are now computed on the fly from one USD base price + a per-region
  exchange rate (see REGIONS below), instead of one hardcoded price column
  per country. This is the key scalability fix: adding a 7th, 8th, 20th
  country is now a one-line data change, not a schema change or a
  find-every-shoe-and-add-a-column exercise.
- Catalog expanded from 6 to 26 shoes to give real coverage across the
  three use-case categories.

A note on the data: toe-box shape / arch-support / width classifications
here are informed general characterizations of these shoe models, not
verified manufacturer specs — meant as practical fit guidance, not a
precision database. Prices are rough USD-anchored estimates converted to
other currencies for convenience; always confirm current price on the
retailer's site before buying.
"""

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote_plus

SHOE_IMAGES_DIR = Path(__file__).parent / "shoe_images"

DB_PATH = Path(__file__).parent / "foofit.db"

# Central place to add/remove supported shopping regions.
# Adding a new country = adding one line here, nothing else in the codebase.
REGIONS = {
    "Global / International": {"currency": "USD", "rate_from_usd": 1.0,  "symbol": "$"},
    "United States":          {"currency": "USD", "rate_from_usd": 1.0,  "symbol": "$"},
    "United Kingdom":         {"currency": "GBP", "rate_from_usd": 0.79, "symbol": "£"},
    "Pakistan":               {"currency": "PKR", "rate_from_usd": 278,  "symbol": "Rs. "},
    "India":                  {"currency": "INR", "rate_from_usd": 83,   "symbol": "₹"},
    "Canada":                 {"currency": "CAD", "rate_from_usd": 1.37, "symbol": "CA$"},
    "United Arab Emirates":   {"currency": "AED", "rate_from_usd": 3.67, "symbol": "AED "},
}

CATEGORIES = ["Everyday / Casual", "Sports & Training", "Medical & Comfort"]
TOE_BOX_SHAPES = ["Round", "Pointed", "Square", "Wide-Anatomical"]
ARCH_TYPES = ["High Arch", "Flat Arch", "Neutral Arch"]
WIDTHS = ["Narrow", "Standard", "Wide", "Extra Wide"]
GENDERS = ["Man", "Woman", "Unisex"]

# Gender classifications below are general demo-level categorizations based
# on how each model is typically marketed, not verified against every
# manufacturer's current size-chart pages — most models are genuinely
# unisex-available, with a handful marketed toward one gender specifically.
_GENDER_OVERRIDES = {
    "Skechers Arch Fit Sunny Bay": "Woman",
    "Rothy's The Point": "Woman",
    "Orthofeet Coral": "Woman",
    "New Balance 928v3": "Man",
    "Dr. Comfort Ranger": "Man",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS shoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    toe_box_shape TEXT NOT NULL,
    arch_support TEXT NOT NULL,
    width TEXT NOT NULL,
    gender TEXT NOT NULL DEFAULT 'Unisex',
    feature TEXT NOT NULL,
    brand_url TEXT NOT NULL,
    base_price_usd REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
"""


def _price_for(base_usd: float, region: str) -> str:
    info = REGIONS.get(region, REGIONS["Global / International"])
    converted = base_usd * info["rate_from_usd"]
    text = f"{converted:,.0f}"
    return f"{info['symbol']}{text}"


def price_and_url(shoe: dict, region: str):
    """
    Given a shoe row and a region name, return (display_price, url).

    The url is a shopping search link for the exact shoe name, not the
    brand's homepage — a direct product-page link would need to be
    manually verified per shoe (26 of them) and would go stale as SKUs
    change, so a search link is the reliable choice: it always resolves
    and reliably surfaces the actual product across retailers.
    """
    price = _price_for(shoe["base_price_usd"], region)
    search_url = f"https://www.google.com/search?tbm=shop&q={quote_plus(shoe['name'])}"
    return price, search_url


# ---- Seed catalog -------------------------------------------------------
SEED_SHOES = [
    # -------- Everyday / Casual --------
    dict(name="New Balance 574", category="Everyday / Casual", toe_box_shape="Round",
         arch_support="Neutral Arch", width="Standard",
         feature="Classic cushioned lifestyle sneaker with a relaxed, roomy fit for all-day wear.",
         brand_url="https://www.newbalance.com", base_price_usd=90),
    dict(name="Skechers Arch Fit Sunny Bay", category="Everyday / Casual", toe_box_shape="Wide-Anatomical",
         arch_support="Flat Arch", width="Wide",
         feature="Built-in podiatrist-certified arch support molded directly into a casual slip-on.",
         brand_url="https://www.skechers.com", base_price_usd=75),
    dict(name="Clarks Un Loop", category="Everyday / Casual", toe_box_shape="Square",
         arch_support="Neutral Arch", width="Standard",
         feature="Structured square toe with a cushioned collar, good for a smart-casual everyday look.",
         brand_url="https://www.clarks.com", base_price_usd=100),
    dict(name="Vans Old Skool", category="Everyday / Casual", toe_box_shape="Round",
         arch_support="Neutral Arch", width="Standard",
         feature="Flat, low-profile skate silhouette; minimal arch structure, best for naturally neutral feet.",
         brand_url="https://www.vans.com", base_price_usd=70),
    dict(name="Cole Haan Grand+ Sneaker", category="Everyday / Casual", toe_box_shape="Round",
         arch_support="Neutral Arch", width="Standard",
         feature="Lightweight dress-casual hybrid with rounded toe and moderate cushioning.",
         brand_url="https://www.colehaan.com", base_price_usd=140),
    dict(name="Allbirds Wool Runner", category="Everyday / Casual", toe_box_shape="Round",
         arch_support="Neutral Arch", width="Wide",
         feature="Breathable knit upper with a naturally wider forefoot fit and soft foam sole.",
         brand_url="https://www.allbirds.com", base_price_usd=98),
    dict(name="ECCO Soft 7", category="Everyday / Casual", toe_box_shape="Round",
         arch_support="Neutral Arch", width="Wide",
         feature="Soft leather casual sneaker with a naturally generous width, popular for wider feet.",
         brand_url="https://www.ecco.com", base_price_usd=130),
    dict(name="Rothy's The Point", category="Everyday / Casual", toe_box_shape="Pointed",
         arch_support="Neutral Arch", width="Narrow",
         feature="Tailored pointed toe knit flat, best suited to narrower, tapered forefeet.",
         brand_url="https://www.rothys.com", base_price_usd=165),

    # -------- Sports & Training --------
    dict(name="Nike Air Zoom Pegasus 40", category="Sports & Training", toe_box_shape="Round",
         arch_support="Neutral Arch", width="Standard",
         feature="Balanced neutral daily trainer on a traditional performance contour.",
         brand_url="https://www.nike.com", base_price_usd=130),
    dict(name="Brooks Adrenaline GTS 23", category="Sports & Training", toe_box_shape="Round",
         arch_support="Flat Arch", width="Standard",
         feature="Structured GuideRail support system designed for overpronating, flatter arches.",
         brand_url="https://www.brooksrunning.com", base_price_usd=140),
    dict(name="Mizuno Wave Rider 27", category="Sports & Training", toe_box_shape="Round",
         arch_support="High Arch", width="Standard",
         feature="Wave plate shock attenuation tuned for rigid, high-arched supinating gaits.",
         brand_url="https://www.mizunousa.com", base_price_usd=140),
    dict(name="Altra Provision 7", category="Sports & Training", toe_box_shape="Wide-Anatomical",
         arch_support="Flat Arch", width="Wide",
         feature="FootShape wide toe box with GuideRail-style stability for flat, pronating feet.",
         brand_url="https://www.altrarunning.com", base_price_usd=150),
    dict(name="Topo Athletic Specter 2", category="Sports & Training", toe_box_shape="Wide-Anatomical",
         arch_support="High Arch", width="Wide",
         feature="Roomy anatomical forefoot with high-rebound cushioning for rigid high arches.",
         brand_url="https://www.topoathletic.com", base_price_usd=165),
    dict(name="Asics Gel-Nimbus 26 Wide", category="Sports & Training", toe_box_shape="Wide-Anatomical",
         arch_support="Neutral Arch", width="Wide",
         feature="Maximum-cushion neutral trainer with extra forefoot volume.",
         brand_url="https://www.asics.com", base_price_usd=160),
    dict(name="Asics Gel-Kayano 30", category="Sports & Training", toe_box_shape="Round",
         arch_support="Flat Arch", width="Standard",
         feature="Long-standing stability trainer built for overpronation control.",
         brand_url="https://www.asics.com", base_price_usd=165),
    dict(name="Hoka Bondi 8", category="Sports & Training", toe_box_shape="Round",
         arch_support="Neutral Arch", width="Wide",
         feature="Maximalist cushioning with a naturally forgiving, wider forefoot fit.",
         brand_url="https://www.hoka.com", base_price_usd=165),
    dict(name="Saucony Guide 16", category="Sports & Training", toe_box_shape="Round",
         arch_support="Flat Arch", width="Standard",
         feature="Mild stability trainer for moderate overpronation, everyday training mileage.",
         brand_url="https://www.saucony.com", base_price_usd=140),
    dict(name="Nike Metcon 9", category="Sports & Training", toe_box_shape="Square",
         arch_support="Neutral Arch", width="Standard",
         feature="Flat, stable platform built for lifting and cross-training, not distance running.",
         brand_url="https://www.nike.com", base_price_usd=150),

    # -------- Medical & Comfort --------
    dict(name="Orthofeet Coral", category="Medical & Comfort", toe_box_shape="Wide-Anatomical",
         arch_support="Flat Arch", width="Extra Wide",
         feature="Seam-free anatomical design with built-in orthotic support, popular for diabetic-friendly fit.",
         brand_url="https://www.orthofeet.com", base_price_usd=135),
    dict(name="Vionic Walker Classic", category="Medical & Comfort", toe_box_shape="Round",
         arch_support="Flat Arch", width="Standard",
         feature="Podiatrist-designed removable orthotic footbed built into a walking shoe.",
         brand_url="https://www.vionicshoes.com", base_price_usd=125),
    dict(name="New Balance 928v3", category="Medical & Comfort", toe_box_shape="Round",
         arch_support="Neutral Arch", width="Extra Wide",
         feature="Frequently recommended by podiatrists for very wide feet needing extra depth.",
         brand_url="https://www.newbalance.com", base_price_usd=150),
    dict(name="Dr. Comfort Ranger", category="Medical & Comfort", toe_box_shape="Wide-Anatomical",
         arch_support="Flat Arch", width="Extra Wide",
         feature="Extra-depth diabetic-friendly design with removable insoles for custom orthotics.",
         brand_url="https://www.drcomfort.com", base_price_usd=145),
    dict(name="Skechers Arch Fit", category="Medical & Comfort", toe_box_shape="Wide-Anatomical",
         arch_support="Flat Arch", width="Wide",
         feature="Molded arch support designed to relieve pressure from flat, overpronating feet.",
         brand_url="https://www.skechers.com", base_price_usd=80),
    dict(name="Brooks Addiction Walker", category="Medical & Comfort", toe_box_shape="Square",
         arch_support="Flat Arch", width="Wide",
         feature="Motion-control walking shoe often recommended for plantar fasciitis and flat feet.",
         brand_url="https://www.brooksrunning.com", base_price_usd=130),
    dict(name="Propet TravelWalker", category="Medical & Comfort", toe_box_shape="Wide-Anatomical",
         arch_support="Neutral Arch", width="Extra Wide",
         feature="Lightweight extra-wide walking shoe designed for swollen or sensitive feet.",
         brand_url="https://www.propetusa.com", base_price_usd=85),
    dict(name="ASICS GEL-Kayano 30 Wide", category="Medical & Comfort", toe_box_shape="Wide-Anatomical",
         arch_support="High Arch", width="Wide",
         feature="Stability platform in an extended width for higher arches needing extra room.",
         brand_url="https://www.asics.com", base_price_usd=165),
]

# Backfill gender onto every seed shoe: use the override if this exact shoe
# is in the list above, otherwise default to Unisex. Doing this here instead
# of typing "gender=..." into all 26 dicts above avoids retyping every entry.
for _s in SEED_SHOES:
    _s["gender"] = _GENDER_OVERRIDES.get(_s["name"], "Unisex")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA)
        count = conn.execute("SELECT COUNT(*) AS c FROM shoes").fetchone()["c"]
        if count == 0:
            for s in SEED_SHOES:
                conn.execute(
                    """INSERT INTO shoes
                       (name, category, toe_box_shape, arch_support, width, gender, feature, brand_url, base_price_usd)
                       VALUES (:name, :category, :toe_box_shape, :arch_support, :width, :gender, :feature, :brand_url, :base_price_usd)""",
                    s,
                )


def all_shoes(category: str = None, gender: str = None):
    """
    gender=None or "Unisex" -> no gender filtering (everything shown).
    gender="Men's" or "Women's" -> shows that gender's shoes PLUS all
    Unisex shoes, never excludes Unisex options.
    """
    with get_conn() as conn:
        sql = "SELECT * FROM shoes WHERE active = 1"
        params = []
        if category:
            sql += " AND category = ?"
            params.append(category)
        if gender and gender != "Unisex":
            sql += " AND (gender = ? OR gender = 'Unisex')"
            params.append(gender)
        sql += " ORDER BY name"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def search_shoes(query: str = "", category: str = None, arch: str = None,
                  width: str = None, gender: str = None, max_price_usd: float = None):
    with get_conn() as conn:
        sql = "SELECT * FROM shoes WHERE active = 1 AND (name LIKE ? OR feature LIKE ?)"
        params = [f"%{query}%", f"%{query}%"]
        if category:
            sql += " AND category = ?"
            params.append(category)
        if arch:
            sql += " AND arch_support = ?"
            params.append(arch)
        if width:
            sql += " AND width = ?"
            params.append(width)
        if gender and gender != "Unisex":
            sql += " AND (gender = ? OR gender = 'Unisex')"
            params.append(gender)
        rows = conn.execute(sql, params).fetchall()
    results = [dict(r) for r in rows]
    if max_price_usd is not None:
        results = [r for r in results if r["base_price_usd"] <= max_price_usd]
    return results


def add_shoe(**fields):
    fields.setdefault("gender", "Unisex")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO shoes
               (name, category, toe_box_shape, arch_support, width, gender, feature, brand_url, base_price_usd)
               VALUES (:name, :category, :toe_box_shape, :arch_support, :width, :gender, :feature, :brand_url, :base_price_usd)""",
            fields,
        )


def shoe_slug(name: str) -> str:
    """Turn a shoe name into a filename-safe slug, e.g. 'Altra Provision 7' -> 'altra-provision-7'."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def shoe_image_path(shoe: dict):
    """
    Return the local image path for a shoe if one has been added to
    shoe_images/, else None. Naming convention: shoe_images/<slug>.jpg
    (also checks .jpeg/.png). This is what lets the try-on flow use the
    catalog photo automatically instead of asking the user to upload one —
    add a file here (see shoe_images/README.md) to enable it per shoe.
    """
    slug = shoe_slug(shoe["name"])
    for ext in (".jpg", ".jpeg", ".png"):
        path = SHOE_IMAGES_DIR / f"{slug}{ext}"
        if path.exists():
            return path
    return None
