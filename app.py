import streamlit as st
from PIL import Image

import database
import matching
import vision
import vto
from styles import get_css, theme_colors, CATEGORY_PILL_CLASS

APP_NAME = "SoleMate AI"

st.set_page_config(page_title=APP_NAME, page_icon="👟", layout="centered")
database.init_db()

if "theme" not in st.session_state:
    st.session_state.theme = "light"

_top_l, _top_r = st.columns([5, 1])
with _top_r:
    theme_choice = st.selectbox(
        "Theme", ["☀️ Light", "🌙 Dark"],
        index=0 if st.session_state.theme == "light" else 1,
        label_visibility="collapsed",
    )
st.session_state.theme = "dark" if "Dark" in theme_choice else "light"

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)
TC = theme_colors(st.session_state.theme)

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-title">👟 {APP_NAME}</div>
        <div class="hero-subtitle">Find your fit. See it on you.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

TOE_SHAPE_OPTIONS = list(matching.TOE_SHAPE_TO_BOX.keys())

# ---------------------------------------------------------------------
# Wizard state
# ---------------------------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "region" not in st.session_state:
    st.session_state.region = list(database.REGIONS.keys())[0]
if "category" not in st.session_state:
    st.session_state.category = database.CATEGORIES[0]
if "toe_shape" not in st.session_state:
    st.session_state.toe_shape = TOE_SHAPE_OPTIONS[0]
if "arch" not in st.session_state:
    st.session_state.arch = "Not sure"
if "width" not in st.session_state:
    st.session_state.width = "Not sure"

TOTAL_STEPS = 4


def go_next():
    st.session_state.step = min(st.session_state.step + 1, TOTAL_STEPS)


def go_back():
    st.session_state.step = max(st.session_state.step - 1, 1)


def go_to(n):
    st.session_state.step = n


st.progress(st.session_state.step / TOTAL_STEPS)
mode = st.radio("Mode", ["🧭 Guided (recommended)", "🔎 Browse everything"], horizontal=True, label_visibility="collapsed")

if mode == "🔎 Browse everything":
    # =================================================================
    # Simple, single-screen browse — no wizard needed here
    # =================================================================
    st.subheader("Browse the catalog")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        query = st.text_input("Search", placeholder="e.g. 'wide' or 'cushion'", label_visibility="collapsed")
    with col_b:
        browse_region = st.selectbox("Region", list(database.REGIONS.keys()), label_visibility="collapsed")

    with st.expander("Filters"):
        f1, f2, f3, f4 = st.columns(4)
        cat_filter = f1.selectbox("Category", ["Any"] + database.CATEGORIES)
        arch_filter = f2.selectbox("Arch", ["Any"] + database.ARCH_TYPES)
        width_filter = f3.selectbox("Width", ["Any"] + database.WIDTHS)
        max_price = f4.number_input("Max $", min_value=0, value=0, step=10)

    results = database.search_shoes(
        query,
        category=None if cat_filter == "Any" else cat_filter,
        arch=None if arch_filter == "Any" else arch_filter,
        width=None if width_filter == "Any" else width_filter,
        max_price_usd=max_price if max_price > 0 else None,
    )
    st.caption(f"{len(results)} shoe(s)")
    for shoe in results:
        price, url = database.price_and_url(shoe, browse_region)
        pill_class = CATEGORY_PILL_CLASS.get(shoe["category"], "pill-everyday")
        st.markdown(
            f"""
            <div class="rec-card">
                <span class="category-pill {pill_class}">{shoe['category']}</span><br>
                <strong>👟 <a href="{url}" target="_blank" style="color:{TC['accent']};text-decoration:underline;">{shoe['name']}</a></strong> — {price}<br>
                <span style="color:{TC['subtext']};font-size:0.9rem;">{shoe['feature']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

else:
    # =================================================================
    # Guided wizard — one decision per screen
    # =================================================================

    # ---- Step 1: What are you shopping for ----
    if st.session_state.step == 1:
        st.markdown("### What are you shopping for?")
        category = st.radio(
            "Category", database.CATEGORIES, label_visibility="collapsed",
            captions=["Daily wear, work, casual", "Running, gym, training", "Extra support, orthopedic-friendly"],
            index=database.CATEGORIES.index(st.session_state.category),
        )
        st.session_state.category = category
        if category == "Medical & Comfort":
            st.caption("ℹ️ Comfort- and support-oriented designs, not medical devices. See a podiatrist for a real foot condition.")
        st.button("Next →", on_click=go_next, type="primary")

    # ---- Step 2: Foot profile (with optional photo scan tucked away) ----
    elif st.session_state.step == 2:
        st.markdown("### Tell us about your foot")
        st.caption("Best guess is fine — you can always adjust your matches later.")

        col1, col2 = st.columns(2)
        with col1:
            st.session_state.toe_shape = st.selectbox(
                "Toe shape", TOE_SHAPE_OPTIONS,
                index=TOE_SHAPE_OPTIONS.index(st.session_state.toe_shape),
            )
            st.session_state.arch = st.selectbox(
                "Arch type", database.ARCH_TYPES + ["Not sure"],
                index=(database.ARCH_TYPES + ["Not sure"]).index(st.session_state.arch),
            )
        with col2:
            st.session_state.width = st.selectbox(
                "Foot width", database.WIDTHS + ["Not sure"],
                index=(database.WIDTHS + ["Not sure"]).index(st.session_state.width),
            )

        with st.expander("Not sure? Quick tips"):
            st.markdown(
                "- **Toe shape:** big toe longest = *Egyptian*, second toe longest = *Greek*, roughly even = *Roman/Square*.\n"
                "- **Arch (wet-footprint test):** wet your foot, step on a paper bag. Whole sole visible = **flat**. "
                "Only heel + ball + thin outer strip = **high**. In between = **neutral**.\n"
                "- **Width:** if your usual sneakers feel tight across the widest part, try Wide."
            )

        with st.expander("📸 Have a photo? Get a calibrated measurement instead"):
            st.caption("Place a standard ID/credit card next to your foot, top-down photo, plain background.")
            uploaded_file = st.file_uploader("Upload foot photo", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
            if uploaded_file is not None:
                manual_length_cm = st.number_input("No card? Enter foot length in cm instead", 15.0, 35.0, 25.0, 0.1)
                use_manual = st.checkbox("Use manual length instead of card detection")

                img = Image.open(uploaded_file)
                st.image(img, width=200)

                if use_manual:
                    px_per_mm, known_len = None, manual_length_cm * 10
                else:
                    px_per_mm, known_len = vision.detect_reference_card(img), None

                result = vision.analyze_foot_contour(img, px_per_mm=px_per_mm, known_length_mm=known_len)

                if result["calibrated"]:
                    st.success(f"📏 Calibrated: {result['width_mm']}mm wide, {result['length_mm']}mm long")
                    ratio = result["width_mm"] / result["length_mm"] if result["length_mm"] else 0.35
                    suggested = "Wide" if ratio > 0.42 else ("Standard" if ratio > 0.38 else "Narrow")
                    if st.button(f"Use suggested width: {suggested}"):
                        st.session_state.width = suggested
                        st.rerun()
                else:
                    st.warning("No card detected — showing shape only, not a real measurement.")

        c1, c2 = st.columns(2)
        c1.button("← Back", on_click=go_back)
        c2.button("Next →", on_click=go_next, type="primary")

    # ---- Step 3: Region (kept tiny, one dropdown) ----
    elif st.session_state.step == 3:
        st.markdown("### Where are you shopping?")
        st.session_state.region = st.selectbox(
            "Region", list(database.REGIONS.keys()), label_visibility="collapsed",
            index=list(database.REGIONS.keys()).index(st.session_state.region),
        )
        c1, c2 = st.columns(2)
        c1.button("← Back", on_click=go_back)
        c2.button("Show my matches →", on_click=go_next, type="primary")

    # ---- Step 4: Results ----
    elif st.session_state.step == 4:
        st.markdown("### Your matches")
        st.button("← Adjust my answers", on_click=go_back)

        all_in_category = database.all_shoes(category=st.session_state.category)
        ranked = matching.rank_shoes(
            all_in_category, st.session_state.category,
            st.session_state.toe_shape, st.session_state.arch, st.session_state.width,
        )

        if not ranked:
            st.info("No shoes in this category yet — try Browse everything above.")
        else:
            pill_class = CATEGORY_PILL_CLASS.get(st.session_state.category, "pill-everyday")
            for score, shoe in ranked:
                price, url = database.price_and_url(shoe, st.session_state.region)
                st.markdown(
                    f"""
                    <div class="rec-card">
                        <span class="category-pill {pill_class}">{shoe['category']}</span><br>
                        <strong>👟 <a href="{url}" target="_blank" style="color:{TC['accent']};text-decoration:underline;">{shoe['name']}</a></strong> — {price}
                        <div class="match-bar-track"><div class="match-bar-fill" style="width:{score}%;"></div></div>
                        <span class="match-pct">{score}% fit match</span><br>
                        <span style="color:{TC['subtext']};font-size:0.9rem;">{shoe['feature']}</span><br>
                        <a href="{url}" target="_blank" class="buy-btn">View Product ↗</a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                with st.expander(f"✨ See it on you — {shoe['name']}"):
                    tc1, tc2 = st.columns(2)
                    with tc1:
                        selfie_file = st.file_uploader("Your photo", type=["jpg", "jpeg", "png"], key=f"selfie_{shoe['id']}")
                    with tc2:
                        shoe_photo_file = st.file_uploader("Shoe photo", type=["jpg", "jpeg", "png"], key=f"shoephoto_{shoe['id']}")

                    adv1, adv2 = st.columns(2)
                    gender = adv1.selectbox("As", ["female", "male"], key=f"gender_{shoe['id']}")
                    style_label = adv2.selectbox("Style", list(vto.STYLES.keys()), key=f"style_{shoe['id']}")
                    style = vto.STYLES[style_label]

                    if st.button("Generate", key=f"tryon_btn_{shoe['id']}", type="primary"):
                        if not selfie_file or not shoe_photo_file:
                            st.warning("Upload both photos first.")
                        else:
                            try:
                                with st.spinner("Generating — up to a minute..."):
                                    result_url = vto.run_tryon_from_uploads(
                                        selfie_file.getvalue(), shoe_photo_file.getvalue(),
                                        gender=gender, style=style,
                                    )
                                st.image(result_url, caption=f"You, wearing {shoe['name']}")
                            except Exception as e:
                                st.error(f"Try-on failed: {e}")

        st.markdown(
            """
            <div class="disclaimer">
            SoleMate AI provides general fit guidance, not a podiatric diagnosis. If you have foot pain, diabetes,
            or another condition affecting your feet, please consult a podiatrist before choosing footwear.
            </div>
            """,
            unsafe_allow_html=True,
        )
