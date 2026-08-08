import streamlit as st
from PIL import Image

import database
import matching
import vision
import vto
from styles import CSS, CATEGORY_PILL_CLASS

st.set_page_config(page_title="FootFit AI Pro", page_icon="👟", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)
database.init_db()

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">👟 FootFit AI Pro</div>
        <div class="hero-subtitle">Foot-shape aware shoe matching for everyday, sport, and comfort-focused footwear</div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_scan, tab_browse = st.tabs(["📸 Scan & Match", "🔎 Browse Catalog"])

TOE_SHAPE_OPTIONS = list(matching.TOE_SHAPE_TO_BOX.keys())

# =====================================================================
# TAB 1 — Guided scan-and-match flow
# =====================================================================
with tab_scan:
    st.markdown('<span class="step-badge">1</span><span class="step-title">Shopping Region</span>', unsafe_allow_html=True)
    selected_region = st.selectbox("Region", list(database.REGIONS.keys()), label_visibility="collapsed")

    st.divider()
    st.markdown('<span class="step-badge">2</span><span class="step-title">What are you shopping for?</span>', unsafe_allow_html=True)
    category = st.radio(
        "Category", database.CATEGORIES, horizontal=True, label_visibility="collapsed",
        captions=["Daily wear, work, casual", "Running, gym, training", "Orthopedic-friendly, extra support"],
    )
    if category == "Medical & Comfort":
        st.caption("ℹ️ These are comfort- and support-oriented shoe designs, not medical devices. If you have foot pain, diabetes, or another condition, please see a podiatrist for personalized advice.")

    st.divider()
    st.markdown('<span class="step-badge">3</span><span class="step-title">Optional: Photo Scan</span>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="guide-box">
        📸 <b>For a calibrated measurement:</b> place a standard ID / credit / debit card flat next to your foot,
        top-down photo, plain background. No card handy? Enter your foot length manually below instead.
        This step is optional — you can also just answer the questions in step 4 directly.
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader("Upload foot photo:", type=["jpg", "png", "jpeg"], label_visibility="collapsed")

    detected_width_mm = detected_length_mm = None
    suggested_width = None
    if uploaded_file is not None:
        use_manual = False
        manual_length_cm = 25.0
        with st.expander("No card in photo? Enter a known foot length instead"):
            manual_length_cm = st.number_input("Foot length in cm (heel to longest toe)", 15.0, 35.0, 25.0, 0.1)
            use_manual = st.checkbox("Use this manual length instead of card detection")

        img = Image.open(uploaded_file)
        st.image(img, caption="Analyzing...", width=240)

        if use_manual:
            px_per_mm, known_len = None, manual_length_cm * 10
        else:
            px_per_mm, known_len = vision.detect_reference_card(img), None

        result = vision.analyze_foot_contour(img, px_per_mm=px_per_mm, known_length_mm=known_len)
        detected_width_mm, detected_length_mm = result["width_mm"], result["length_mm"]

        if result["calibrated"]:
            st.markdown('<span class="accuracy-badge accuracy-calibrated">📏 Calibrated measurement</span>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Forefoot Width", f"{detected_width_mm} mm")
            c2.metric("Foot Length", f"{detected_length_mm} mm")
            approx_size = vision.mm_to_us_shoe_size(detected_length_mm)
            c3.metric("Est. US Size", f"{approx_size}")
            # rough width bucket suggestion from measured ratio, still just a suggestion
            ratio = detected_width_mm / detected_length_mm if detected_length_mm else 0.35
            if ratio > 0.42:
                suggested_width = "Wide"
            elif ratio > 0.38:
                suggested_width = "Standard"
            else:
                suggested_width = "Narrow"
            st.caption(f"Based on this photo, **{suggested_width}** width may be a good starting point below — adjust if it doesn't match how your shoes usually fit.")
        else:
            st.markdown('<span class="accuracy-badge accuracy-estimate">🔍 Shape estimate only — no calibration</span>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<span class="step-badge">4</span><span class="step-title">Your Foot Profile</span>', unsafe_allow_html=True)

    with st.expander("🧭 Not sure about toe shape or arch type? Quick self-check tips"):
        st.markdown(
            "- **Toe shape:** Look straight down at your bare foot. Is your big toe clearly the longest "
            "(*Egyptian*), is your second toe longest (*Greek*), or are your toes roughly even (*Roman/Square*)?\n"
            "- **Arch type — the wet-footprint test:** Wet the sole of your foot and step onto a paper bag or "
            "dark pavement. A footprint showing almost the whole sole suggests a **flat arch**. A footprint "
            "showing only your heel, ball, and a thin outer strip suggests a **high arch**. Something in "
            "between is a **neutral arch**."
        )

    col1, col2 = st.columns(2)
    with col1:
        toe_shape = st.selectbox("Toe shape", TOE_SHAPE_OPTIONS)
        arch = st.selectbox("Arch type", database.ARCH_TYPES + ["Not sure"])
    with col2:
        width_default_index = database.WIDTHS.index(suggested_width) if suggested_width in database.WIDTHS else 1
        width = st.selectbox("Foot width", database.WIDTHS + ["Not sure"], index=width_default_index)
        st.caption("Width tip: if your usual sneakers feel tight across the widest part of your forefoot, try Wide or Extra Wide.")

    st.divider()
    st.markdown('<span class="step-badge">5</span><span class="step-title">Your Matches</span>', unsafe_allow_html=True)

    all_in_category = database.all_shoes(category=category)
    ranked = matching.rank_shoes(all_in_category, category, toe_shape, arch, width)

    if not ranked:
        st.info("No shoes in this category yet — try Browse Catalog, or check back as we add more.")
    else:
        pill_class = CATEGORY_PILL_CLASS.get(category, "pill-everyday")
        for score, shoe in ranked:
            price, url = database.price_and_url(shoe, selected_region)
            st.markdown(
                f"""
                <div class="rec-card">
                    <span class="category-pill {pill_class}">{shoe['category']}</span><br>
                    <strong>👟 <a href="{url}" target="_blank" style="color:#38BDF8;text-decoration:underline;">{shoe['name']}</a></strong> — {price}
                    <div class="match-bar-track"><div class="match-bar-fill" style="width:{score}%;"></div></div>
                    <span class="match-pct">{score}% fit match</span><br>
                    <span style="color:#CBD5E1;font-size:0.92rem;">
                        <b>Toe box:</b> {shoe['toe_box_shape']} &nbsp;|&nbsp; <b>Arch:</b> {shoe['arch_support']} &nbsp;|&nbsp; <b>Width:</b> {shoe['width']}
                    </span><br>
                    <span style="color:#CBD5E1;font-size:0.9rem;">{shoe['feature']}</span><br>
                    <a href="{url}" target="_blank" class="buy-btn">View Product ↗</a>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.expander(f"👗 Try on {shoe['name']} — powered by YouCam AI Shoes API"):
                tc1, tc2 = st.columns(2)
                with tc1:
                    selfie_file = st.file_uploader(
                        "Your photo (face + legs/feet visible works best)",
                        type=["jpg", "jpeg", "png"], key=f"selfie_{shoe['id']}",
                    )
                with tc2:
                    shoe_photo_file = st.file_uploader(
                        "Photo of this shoe (product shot or worn-on-foot)",
                        type=["jpg", "jpeg", "png"], key=f"shoephoto_{shoe['id']}",
                    )
                gender = st.selectbox("Visualize as", ["female", "male"], key=f"gender_{shoe['id']}")
                style_label = st.selectbox("Style", list(vto.STYLES.keys()), key=f"style_{shoe['id']}")
                style = vto.STYLES[style_label]

                if st.button("✨ Generate Try-On", key=f"tryon_btn_{shoe['id']}"):
                    if not selfie_file or not shoe_photo_file:
                        st.warning("Upload both your photo and a shoe photo first.")
                    else:
                        try:
                            with st.spinner("Generating your try-on — this can take up to a minute..."):
                                result_url = vto.run_tryon_from_uploads(
                                    selfie_file.getvalue(), shoe_photo_file.getvalue(),
                                    gender=gender, style=style,
                                )
                            st.image(result_url, caption=f"You, wearing {shoe['name']}")
                        except Exception as e:
                            st.error(f"Try-on failed: {e}")
                            st.caption("Check that YOUCAM_API_KEY is set correctly in secrets, and that your API units haven't run out.")

    st.markdown(
        """
        <div class="disclaimer">
        FootFit AI provides general fit guidance based on self-reported and photo-estimated foot characteristics.
        It is not a podiatric diagnosis and is not a substitute for professional medical advice. If you have foot pain,
        diabetes, arthritis, or another condition affecting your feet, please consult a podiatrist or other qualified
        healthcare provider before choosing footwear.
        </div>
        """,
        unsafe_allow_html=True,
    )

# =====================================================================
# TAB 2 — Browse / search the full catalog
# =====================================================================
with tab_browse:
    st.subheader("Search the full catalog")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        query = st.text_input("Search by name or feature", placeholder="e.g. 'wide' or 'cushion'")
    with col_b:
        browse_region = st.selectbox("Region", list(database.REGIONS.keys()), key="browse_region")

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        cat_filter = st.selectbox("Category", ["Any"] + database.CATEGORIES)
    with f2:
        arch_filter = st.selectbox("Arch", ["Any"] + database.ARCH_TYPES)
    with f3:
        width_filter = st.selectbox("Width", ["Any"] + database.WIDTHS)
    with f4:
        max_price = st.number_input("Max price (USD)", min_value=0, value=0, step=10, help="0 = no limit")

    results = database.search_shoes(
        query,
        category=None if cat_filter == "Any" else cat_filter,
        arch=None if arch_filter == "Any" else arch_filter,
        width=None if width_filter == "Any" else width_filter,
        max_price_usd=max_price if max_price > 0 else None,
    )
    st.caption(f"{len(results)} shoe(s) found")

    for shoe in results:
        price, url = database.price_and_url(shoe, browse_region)
        pill_class = CATEGORY_PILL_CLASS.get(shoe["category"], "pill-everyday")
        st.markdown(
            f"""
            <div class="rec-card">
                <span class="category-pill {pill_class}">{shoe['category']}</span><br>
                <strong>👟 <a href="{url}" target="_blank" style="color:#38BDF8;text-decoration:underline;">{shoe['name']}</a></strong> — {price}<br>
                <span style="color:#CBD5E1;font-size:0.92rem;">
                    <b>Toe box:</b> {shoe['toe_box_shape']} &nbsp;|&nbsp; <b>Arch:</b> {shoe['arch_support']} &nbsp;|&nbsp; <b>Width:</b> {shoe['width']}
                </span><br>
                <span style="color:#CBD5E1;font-size:0.9rem;">{shoe['feature']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
