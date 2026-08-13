# Solefit

## v3 update — categories, richer foot-shape matching, more regions

**New shopping categories:** Everyday / Casual, Sports & Training, Medical & Comfort. Category is a hard filter — you pick what kind of shoe you're shopping for first, then get matches within that category.

**Richer, more accurate foot-shape input:**
- **Toe shape** (Egyptian / Greek / Roman-Square / Not sure) — this is about *your* foot, and maps to which *shoe* toe-box shapes (Round / Pointed / Square / Wide-Anatomical) tend to fit that toe shape best. See `matching.py` for the reasoning and mapping.
- **Arch type**, now with an in-app explanation of the classic wet-footprint self-test, so people can answer accurately even without a photo.
- **Foot width**, with a plain-language tip for figuring it out from how current shoes fit.
- The photo scan (still optional) now *feeds into* these dropdowns as a suggested starting point rather than being the only path in.

**Ranked matching instead of exact-match filtering:** the old version only showed shoes if every attribute matched exactly, which often showed nothing. Now every shoe in the chosen category gets a 0–100 fit score (see `matching.py`), and you always see your best available options, ranked, with a visible match-percentage bar.

**More regions, scalably:** `database.py` now has a single `REGIONS` dictionary (US, UK, Pakistan, India, Canada, UAE, Global) with one exchange rate each — prices are computed from one USD base price per shoe. Adding a 7th or 20th country going forward is a one-line addition to that dictionary, not a new database column or a rewrite of every shoe.

**Catalog grown from 6 to 26 shoes**, spread across the three categories, with more will to add over time via `database.add_shoe(...)`.

**Interface refresh:** gradient hero header, category color tags, animated match-score bars, custom fonts (Poppins/Inter) — meant to feel more like a product than a script.

**Important scope note:** this app gives general **fit and comfort guidance**, not podiatric diagnosis. It cannot detect or treat actual foot conditions (plantar fasciitis, bunions, diabetic foot complications, etc.). The "Medical & Comfort" category surfaces orthopedic-friendly, supportive shoe designs — it does not mean the app is providing medical advice. A visible disclaimer is shown on the Scan & Match tab for exactly this reason. If you want to expand into real podiatric use, that would need a licensed professional's input on the recommendation logic, not just more code.

---

## What changed from the original version

**Structure** — split one 228-line file into four focused ones:
- `app.py` — UI only
- `database.py` — the shoe catalog, now a real SQLite database
- `vision.py` — foot photo analysis
- `styles.py` — CSS

This matters mainly for *you and future AI-assisted edits*: when something breaks or you want to change one piece (say, add a new region), the AI helping you only needs to look at one small, relevant file instead of untangling everything at once.

**Catalog → real database** — `foofit.db` (SQLite) replaces the hardcoded Python list. It supports:
- Filtering by exact shape + arch match (the recommendation engine)
- Free-text search + price filtering (new "Browse Catalog" tab)
- Adding shoes via `database.add_shoe(...)` without touching `app.py`

**Accurate measurement (calibrated)** — the old version invented a width in millimeters from a made-up formula. Now:
- If you place a standard ID/credit/debit card next to your foot in the photo, the app detects it and uses its known real-world size (85.6mm × 53.98mm) to convert pixels → real millimeters. This gives an actual calibrated measurement.
- If no card is detected, you can manually enter your foot length (measured with a ruler) instead.
- If neither is available, the app clearly labels the result as a **shape estimate only** — it will never silently show a fake number as if it were real. Look for the green "Calibrated measurement" badge vs. the amber "Shape estimate only" badge.

**Fixed a deployment bug** — swapped `opencv-python` for `opencv-python-headless` in requirements. The former needs system GUI libraries that often aren't installed on cloud servers and can cause deploy failures; the headless version is built for exactly this use case.

**Theming** — added `.streamlit/config.toml` so the app uses a consistent dark theme by default instead of Streamlit's default look.

## Running locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
The first run creates `foofit.db` automatically and seeds it with the original 6 shoes.

## Adding shoes to the catalog
Don't edit `app.py`. Instead, from a Python shell in the project folder:
```python
import database
database.add_shoe(
    name="New Shoe Name",
    toe_box="Wide / Fan-Shaped Forefoot",       # must exactly match existing values
    arch_support="Neutral Arch",                 # must exactly match existing values
    feature="One sentence on what makes it fit this profile.",
    price_usd="$120", price_gbp="£110", price_pkr="Rs. 34,000",
    url_us="https://...", url_uk="https://...", url_pk="https://...",
)
```
As of v3, use these fields instead: `name, category, toe_box_shape, arch_support, width, feature, brand_url, base_price_usd`.
Valid `category`: `"Everyday / Casual"`, `"Sports & Training"`, `"Medical & Comfort"`
Valid `toe_box_shape`: `"Round"`, `"Pointed"`, `"Square"`, `"Wide-Anatomical"`
Valid `arch_support`: `"High Arch"`, `"Flat Arch"`, `"Neutral Arch"`
Valid `width`: `"Narrow"`, `"Standard"`, `"Wide"`, `"Extra Wide"`
`base_price_usd` is a number (e.g. `130`) — all regional prices are calculated from this automatically using the exchange rates in `database.REGIONS`.

As the catalog grows past a few dozen shoes, or if you want to add a proper admin screen for editing shoes without Python, that's a natural next step — just ask.

## Deploying
Same as before — push to GitHub, deploy via Streamlit Community Cloud pointing at `app.py`. `foofit.db` will be created fresh on first run on the server (the seed data ships with the code, not the database file itself).

**Note on Streamlit Cloud + SQLite:** Streamlit Cloud's filesystem is not permanently persistent across app restarts/redeploys — any shoes you add via `add_shoe()` directly on the deployed app could be lost on redeploy. For now that's fine since the catalog is edited by you, not by end users. If you later want end users' data (like saved measurements) to persist reliably, that's the point where moving to a small hosted database (e.g. free-tier Supabase Postgres) makes sense — happy to wire that up when you're there.

## Honest limitations that remain
- Shape classification (wide vs. standard) is still a heuristic based on aspect ratio, not a trained model. It's a reasonable first pass but will misclassify some feet, especially at odd camera angles.
- Card detection can fail on cluttered backgrounds or poor lighting — the manual-length fallback exists for exactly this reason.
- This is not a medical device and shouldn't be treated as podiatric advice.
