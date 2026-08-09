import streamlit as st
from PIL import Image


def html_block(s: str) -> str:
    """
    Strip leading whitespace from every line before handing HTML to st.markdown.
    Without this, deeply-nested f-strings (lots of Python indentation) get
    enough leading spaces that the browser's markdown renderer treats them
    as a preformatted code block instead of real HTML — which is exactly
    what was happening to the shoe cards.
    """
    lines = s.strip("\n").split("\n")
    return "\n".join(line.strip() for line in lines)

import database
import matching
import vision
import vto
from styles import get_css, theme_colors, CATEGORY_PILL_CLASS, CATEGORY_ICON

APP_NAME = "SoleMate"

st.set_page_config(page_title=APP_NAME, page_icon="👟", layout="centered")
database.init_db()

st.markdown(get_css("light"), unsafe_allow_html=True)
TC = theme_colors("light")

st.markdown(
    html_block(f"""
    <div class="hero">
        <div class="hero-title">👟 {APP_NAME}</div>
        <div class="hero-subtitle">Find your fit. See it on you.</div>
    </div>
    """),
    unsafe_allow_html=True,
)

TOE_SHAPE_OPTIONS = list(matching.TOE_SHAPE_TO_BOX.keys())

# ---------------------------------------------------------------------
# Wizard state
# ---------------------------------------------------------------------
if "gender" not in st.session_state:
    st.session_state.gender = "Unisex"
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

TOTAL_STEPS = 5


def go_next():
    st.session_state.step = min(st.session_state.step + 1, TOTAL_STEPS)


def go_back():
    st.session_state.step = max(st.session_state.step - 1, 1)


def go_to(n):
    st.session_state.step = n


GENDER_TO_VTO = {"Men's": "male", "Women's": "female", "Unisex": "female"}

STEP_LABELS = {
    1: "Step 1 of 5 · Who's this for",
    2: "Step 2 of 5 · What you're shopping for",
    3: "Step 3 of 5 · Your foot profile",
    4: "Step 4 of 5 · Shopping region",
    5: "Step 5 of 5 · Your matches",
}

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
        icon = CATEGORY_ICON.get(shoe["category"], "👟")
        st.markdown(
            html_block(f"""
            <div class="rec-card">
                <span class="category-pill {pill_class}">{shoe['category']}</span><br>
                <strong>{icon} <a href="{url}" target="_blank" style="color:{TC['accent']};text-decoration:underline;">{shoe['name']}</a></strong> — {price}<br>
                <span style="color:{TC['subtext']};font-size:0.9rem;">{shoe['feature']}</span>
            </div>
            """),
            unsafe_allow_html=True,
        )

else:
    # =================================================================
    # Guided wizard — one decision per screen
    # =================================================================

    # ---- Step 1: Who's this for (gender) ----
    if st.session_state.step == 1:
        st.markdown(f'<div class="step-label">{STEP_LABELS[1]}</div>', unsafe_allow_html=True)
        st.markdown("### Who's this for?")
        st.caption("This tailors which shoes get suggested to you.")
        gender = st.radio(
            "Gender", database.GENDERS, label_visibility="collapsed", horizontal=True,
            index=database.GENDERS.index(st.session_state.gender),
        )
        st.session_state.gender = gender
        st.button("Next →", on_click=go_next, type="primary")

    # ---- Step 2: What are you shopping for ----
    elif st.session_state.step == 2:
        st.markdown(f'<div class="step-label">{STEP_LABELS[2]}</div>', unsafe_allow_html=True)
        st.markdown("### What are you shopping for?")
        category = st.radio(
            "Category", database.CATEGORIES, label_visibility="collapsed",
            captions=["Daily wear, work, casual", "Running, gym, training", "Extra support, orthopedic-friendly"],
            index=database.CATEGORIES.index(st.session_state.category),
        )
        st.session_state.category = category
        if category == "Medical & Comfort":
            st.caption("ℹ️ Comfort- and support-oriented designs, not medical devices. See a podiatrist for a real foot condition.")
        c1, c2 = st.columns(2)
        c1.button("← Back", on_click=go_back)
        c2.button("Next →", on_click=go_next, type="primary")

    # ---- Step 3: Foot profile (with optional photo scan tucked away) ----
    elif st.session_state.step == 3:
        st.markdown(f'<div class="step-label">{STEP_LABELS[3]}</div>', unsafe_allow_html=True)
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
            st.markdown(
                "**How to get an accurate reading:**\n"
                "1. Place a standard ID, credit, or debit card flat on the floor next to your bare foot\n"
                "2. Hold your phone directly overhead (top-down, not at an angle)\n"
                "3. Make sure your whole foot AND the whole card are visible in frame\n"
                "4. Use a plain floor, and make sure lighting is even (no strong shadows across your foot)"
            )
            capture_mode = st.radio(
                "How do you want to provide the photo?", ["📁 Upload a photo", "📷 Take a photo now"],
                horizontal=True, label_visibility="collapsed", key="calib_capture_mode",
            )
            if capture_mode == "📷 Take a photo now":
                uploaded_file = st.camera_input("Line up your foot + card, then capture", label_visibility="collapsed")
            else:
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
                    st.warning("No card detected in that photo — try recapturing with the card flatter and more visible, or enter your foot length manually above.")

        c1, c2 = st.columns(2)
        c1.button("← Back", on_click=go_back)
        c2.button("Next →", on_click=go_next, type="primary")

    # ---- Step 4: Region (kept tiny, one dropdown) ----
    elif st.session_state.step == 4:
        st.markdown(f'<div class="step-label">{STEP_LABELS[4]}</div>', unsafe_allow_html=True)
        st.markdown("### Where are you shopping?")
        st.session_state.region = st.selectbox(
            "Region", list(database.REGIONS.keys()), label_visibility="collapsed",
            index=list(database.REGIONS.keys()).index(st.session_state.region),
        )
        c1, c2 = st.columns(2)
        c1.button("← Back", on_click=go_back)
        c2.button("Show my matches →", on_click=go_next, type="primary")

    # ---- Step 5: Results ----
    elif st.session_state.step == 5:
        st.markdown(f'<div class="step-label">{STEP_LABELS[5]}</div>', unsafe_allow_html=True)
        st.markdown("### Nice! Here are your best matches")
        st.button("← Adjust my answers", on_click=go_back)

        all_in_category = database.all_shoes(category=st.session_state.category, gender=st.session_state.gender)
        ranked = matching.rank_shoes(
            all_in_category, st.session_state.category,
            st.session_state.toe_shape, st.session_state.arch, st.session_state.width,
        )

        if not ranked:
            st.info("No shoes in this category yet — try Browse everything above.")
        else:
            pill_class = CATEGORY_PILL_CLASS.get(st.session_state.category, "pill-everyday")
            icon = CATEGORY_ICON.get(st.session_state.category, "👟")
            for i, (score, shoe) in enumerate(ranked):
                price, url = database.price_and_url(shoe, st.session_state.region)
                card_class = "rec-card top-match" if i == 0 else "rec-card"
                badge_html = '<span class="best-match-badge">🏆 BEST MATCH</span><br>' if i == 0 else ""
                st.markdown(
                    html_block(f"""
                    <div class="{card_class}">
                        {badge_html}
                        <span class="category-pill {pill_class}">{shoe['category']}</span><br>
                        <strong>{icon} <a href="{url}" target="_blank" style="color:{TC['accent']};text-decoration:underline;">{shoe['name']}</a></strong> — {price}
                        <div class="match-bar-track"><div class="match-bar-fill" style="width:{score}%;"></div></div>
                        <span class="match-pct">{score}% fit match</span><br>
                        <span style="color:{TC['subtext']};font-size:0.9rem;">{shoe['feature']}</span><br>
                        <a href="{url}" target="_blank" class="buy-btn">View Product ↗</a>
                    </div>
                    """),
                    unsafe_allow_html=True,
                )

                with st.expander(f"✨ See it on you — {shoe['name']}"):
                    catalog_image_path = database.shoe_image_path(shoe)

                    st.markdown(
                        "**For the best result:** stand facing the camera, full body or at least legs "
                        "and feet visible, plain background, good even lighting."
                    )
                    selfie_mode = st.radio(
                        "How do you want to provide your photo?", ["📁 Upload a photo", "📷 Take a photo now"],
                        horizontal=True, label_visibility="collapsed", key=f"selfie_mode_{shoe['id']}",
                    )

                    if catalog_image_path:
                        st.image(str(catalog_image_path), width=140, caption=shoe['name'])
                        if selfie_mode == "📷 Take a photo now":
                            selfie_file = st.camera_input("Stand back so your legs are in frame, then capture", label_visibility="collapsed", key=f"selfie_cam_{shoe['id']}")
                        else:
                            selfie_file = st.file_uploader("Your photo", type=["jpg", "jpeg", "png"], key=f"selfie_{shoe['id']}")
                    else:
                        st.caption("No catalog photo for this shoe yet — upload one to try it on for now.")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if selfie_mode == "📷 Take a photo now":
                                selfie_file = st.camera_input("Your photo", label_visibility="collapsed", key=f"selfie_cam_{shoe['id']}")
                            else:
                                selfie_file = st.file_uploader("Your photo", type=["jpg", "jpeg", "png"], key=f"selfie_{shoe['id']}")
                        fallback_shoe_file = col_b.file_uploader("Shoe photo", type=["jpg", "jpeg", "png"], key=f"shoephoto_{shoe['id']}")

                    gender = GENDER_TO_VTO.get(st.session_state.gender, "female")
                    style_label = st.selectbox("Style", list(vto.STYLES.keys()), key=f"style_{shoe['id']}")
                    style = vto.STYLES[style_label]

                    if st.button("Generate", key=f"tryon_btn_{shoe['id']}", type="primary"):
                        shoe_bytes = None
                        if catalog_image_path:
                            shoe_bytes = catalog_image_path.read_bytes()
                        elif fallback_shoe_file:
                            shoe_bytes = fallback_shoe_file.getvalue()

                        if not selfie_file or not shoe_bytes:
                            st.warning("Upload your photo first" if catalog_image_path else "Upload both photos first.")
                        else:
                            try:
                                with st.spinner("Generating — up to a minute..."):
                                    result_url = vto.run_tryon_from_uploads(
                                        selfie_file.getvalue(), shoe_bytes,
                                        gender=gender, style=style,
                                    )
                                st.image(result_url, caption=f"You, wearing {shoe['name']}")
                            except Exception as e:
                                st.error(f"Try-on failed: {e}")

        st.markdown(
            html_block("""
            <div class="disclaimer">
            SoleMate provides general fit guidance, not a podiatric diagnosis. If you have foot pain, diabetes,
            or another condition affecting your feet, please consult a podiatrist before choosing footwear.
            </div>
            """),
            unsafe_allow_html=True,
        )
