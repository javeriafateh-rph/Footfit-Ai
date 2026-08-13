FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500&display=swap');"

ACCENT_POP = "#F43F5E"  # warm coral/rose — used sparingly for "pop" highlights against the blue/indigo base palette

CATEGORY_PILL_CLASS = {
    "Everyday / Casual": "pill-everyday",
    "Sports & Training": "pill-sports",
    "Medical & Comfort": "pill-medical",
}

CATEGORY_ICON = {
    "Everyday / Casual": "👞",
    "Sports & Training": "🏃",
    "Medical & Comfort": "🦶",
}


def _build_css(*, bg, card_bg, card_border, text, subtext, heading, accent, accent_hover,
                guide_bg, guide_border, pill_everyday_bg, pill_everyday_text,
                pill_sports_bg, pill_sports_text, pill_medical_bg, pill_medical_text,
                badge_ok_bg, badge_ok_text, badge_warn_bg, badge_warn_text,
                track_bg, disclaimer_bg, disclaimer_text, app_bg):
    return f"""
    <style>
    {FONT_IMPORT}

    :root {{
        --primary-color: {accent};
        --background-color: {app_bg};
        --secondary-background-color: {card_bg};
        --text-color: {text};
    }}

    .stApp {{ background-color: {app_bg}; }}
    html, body, [class*="css"]  {{ font-family: 'Inter', sans-serif; color: {text}; }}

    /* Force native Streamlit widget text/labels to follow OUR theme choice,
       regardless of what .streamlit/config.toml has baked in — this is what
       was causing invisible text when the in-app toggle disagreed with the
       static config file. */
    .stApp, .stApp p, .stApp span, .stApp label, .stApp div,
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
    [data-testid="stWidgetLabel"] p, .stRadio label, .stSelectbox label,
    .stCaption, .stCaption p, [data-testid="stCaptionContainer"] {{
        color: {text} !important;
    }}
    .stRadio [data-baseweb="radio"] div:first-child {{
        border-color: {subtext} !important;
    }}
    .stSelectbox > div > div, .stTextInput > div > div, .stNumberInput > div > div {{
        background-color: {card_bg} !important;
        color: {text} !important;
        border-color: {card_border} !important;
    }}

    .hero {{
        background-color: {bg};
        background-image:
            radial-gradient(circle, {card_border} 1px, transparent 1px),
            radial-gradient(circle at 15% 20%, rgba(14,165,233,0.10), transparent 45%),
            radial-gradient(circle at 85% 25%, rgba(99,102,241,0.10), transparent 45%);
        background-size: 22px 22px, auto, auto;
        background-position: center, center, center;
        border: 1px solid {card_border};
        border-radius: 18px;
        padding: 30px 24px;
        text-align: center;
        margin-bottom: 26px;
        box-shadow: 0 2px 12px rgba(15,23,42,0.06);
        position: relative;
        overflow: hidden;
    }}
    .hero-title {{
        font-family: 'Poppins', sans-serif;
        font-size: 2.1rem;
        font-weight: 700;
        color: {heading};
        margin: 0;
        letter-spacing: -0.01em;
        position: relative;
        z-index: 1;
    }}
    .hero-subtitle {{ color: {subtext}; font-size: 1.02rem; margin-top: 8px; position: relative; z-index: 1; }}

    .tagline {{
        display: inline-block;
        margin-top: 16px;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        font-size: 0.95rem;
        color: {accent};
        letter-spacing: 0.01em;
        position: relative;
        z-index: 1;
    }}

    .step-badge {{
        display: inline-block;
        background-color: {accent};
        color: white;
        border-radius: 999px;
        width: 28px; height: 28px;
        text-align: center;
        line-height: 28px;
        font-weight: 700;
        margin-right: 8px;
        font-size: 0.85rem;
    }}
    .step-title {{ font-family: 'Poppins', sans-serif; font-weight: 600; font-size: 1.15rem; color: {heading}; }}

    .guide-box {{
        background-color: {guide_bg};
        border: 1px dashed {guide_border};
        padding: 12px 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        color: {text};
        font-size: 0.9rem;
    }}

    .card {{
        background-color: {card_bg};
        border-left: 5px solid {accent};
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        color: {text};
    }}
    .card h4 {{ color: {accent} !important; margin-top: 0px; font-family: 'Poppins', sans-serif; }}

    .rec-card {{
        background-color: {card_bg};
        border: 1px solid {card_border};
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 14px;
        color: {text};
        box-shadow: 0 1px 4px rgba(15,23,42,0.04);
        transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
    }}
    .rec-card:hover {{ border-color: {accent}; box-shadow: 0 4px 14px rgba(15,23,42,0.08); transform: translateY(-1px); }}
    .rec-card strong {{ font-size: 1.15rem; color: {accent}; font-family: 'Poppins', sans-serif; }}

    .rec-card.top-match {{
        border: 2px solid {accent};
        box-shadow: 0 4px 14px rgba(14,165,233,0.15);
        position: relative;
    }}
    .best-match-badge {{
        display: inline-block;
        background-color: {accent};
        color: #FFFFFF;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 999px;
        margin-bottom: 8px;
        letter-spacing: 0.02em;
    }}

    .step-label {{
        color: {subtext};
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }}

    /* Editorial serif treatment for the big step headlines (h3 from st.markdown "### ...") */
    [data-testid="stMarkdownContainer"] h3 {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        color: {heading};
        letter-spacing: -0.01em;
    }}

    /* Numbered step indicator — nodes connected by lines, replaces the flat progress bar */
    .step-indicator {{
        display: flex;
        align-items: flex-start;
        justify-content: center;
        gap: 2px;
        margin: 4px 0 22px 0;
        flex-wrap: nowrap;
        overflow-x: auto;
    }}
    .step-node {{
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 46px;
    }}
    .step-node-circle {{
        width: 26px;
        height: 26px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.72rem;
        font-weight: 700;
        border: 2px solid {card_border};
        color: {subtext};
        background-color: {bg};
        transition: all 0.2s ease;
    }}
    .step-node.active .step-node-circle {{
        border-color: {ACCENT_POP};
        color: {ACCENT_POP};
        background-color: {bg};
        box-shadow: 0 0 0 3px {ACCENT_POP}22;
    }}
    .step-node.done .step-node-circle {{
        border-color: {accent};
        background-color: {accent};
        color: #FFFFFF;
    }}
    .step-node-label {{
        font-size: 0.62rem;
        color: {subtext};
        margin-top: 4px;
        text-align: center;
        max-width: 60px;
        line-height: 1.15;
    }}
    .step-node.active .step-node-label {{ color: {ACCENT_POP}; font-weight: 600; }}
    .step-node.done .step-node-label {{ color: {accent}; }}
    .step-connector {{
        height: 2px;
        width: 24px;
        background-color: {card_border};
        margin-top: 12px;
        flex-shrink: 0;
    }}
    .step-connector.done {{ background-color: {accent}; }}

    .match-bar-track {{
        background-color: {track_bg};
        border-radius: 999px;
        height: 8px;
        width: 100%;
        margin: 8px 0 10px 0;
        overflow: hidden;
    }}
    .match-bar-fill {{ height: 100%; border-radius: 999px; background-color: {accent}; }}
    .match-pct {{ font-size: 0.8rem; color: {accent}; font-weight: 600; }}

    .buy-btn {{
        display: inline-block;
        background-color: {accent};
        color: #FFFFFF !important;
        font-weight: 600;
        padding: 8px 18px;
        border-radius: 999px;
        text-decoration: none;
        margin-top: 10px;
        font-size: 0.9rem;
    }}
    .buy-btn:hover {{ background-color: {accent_hover}; }}

    .category-pill {{
        display: inline-block;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 8px;
    }}
    .pill-everyday {{ background-color: {pill_everyday_bg}; color: {pill_everyday_text}; }}
    .pill-sports {{ background-color: {pill_sports_bg}; color: {pill_sports_text}; }}
    .pill-medical {{ background-color: {pill_medical_bg}; color: {pill_medical_text}; }}

    .accuracy-badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-left: 8px;
    }}
    .accuracy-calibrated {{ background-color: {badge_ok_bg}; color: {badge_ok_text}; }}
    .accuracy-estimate {{ background-color: {badge_warn_bg}; color: {badge_warn_text}; }}

    .disclaimer {{
        background-color: {disclaimer_bg};
        border-radius: 10px;
        padding: 12px 16px;
        font-size: 0.82rem;
        color: {disclaimer_text};
        margin-top: 24px;
    }}

    .footer-credit {{
        text-align: center;
        color: {subtext};
        font-size: 0.8rem;
        margin-top: 14px;
        padding-top: 14px;
        border-top: 1px solid {card_border};
    }}
    .footer-credit a {{ color: {accent}; text-decoration: none; font-weight: 500; }}
    </style>
    """


LIGHT_CSS = _build_css(
    bg="#FFFFFF", card_bg="#FFFFFF", card_border="#E5E7EB", text="#1F2937", subtext="#6B7280",
    heading="#0F172A", accent="#0EA5E9", accent_hover="#0284C7",
    guide_bg="#F0F9FF", guide_border="#7DD3FC",
    pill_everyday_bg="#E0F2FE", pill_everyday_text="#0369A1",
    pill_sports_bg="#FEF3C7", pill_sports_text="#92400E",
    pill_medical_bg="#DCFCE7", pill_medical_text="#166534",
    badge_ok_bg="#DCFCE7", badge_ok_text="#166534",
    badge_warn_bg="#FEF3C7", badge_warn_text="#92400E",
    track_bg="#E5E7EB", disclaimer_bg="#F3F4F6", disclaimer_text="#6B7280",
    app_bg="#FAFAFA",
)

DARK_CSS = _build_css(
    bg="#0F172A", card_bg="#0F172A", card_border="#2B3A55", text="#F8FAFC", subtext="#94A3B8",
    heading="#F8FAFC", accent="#38BDF8", accent_hover="#0EA5E9",
    guide_bg="#0F172A", guide_border="#38BDF8",
    pill_everyday_bg="#164E63", pill_everyday_text="#A5F3FC",
    pill_sports_bg="#713F12", pill_sports_text="#FDE68A",
    pill_medical_bg="#14532D", pill_medical_text="#BBF7D0",
    badge_ok_bg="#065F46", badge_ok_text="#D1FAE5",
    badge_warn_bg="#78350F", badge_warn_text="#FEF3C7",
    track_bg="#1E293B", disclaimer_bg="#1F2937", disclaimer_text="#9CA3AF",
    app_bg="#0B1120",
)


def get_css(theme: str) -> str:
    return DARK_CSS if theme == "dark" else LIGHT_CSS


def theme_colors(theme: str) -> dict:
    """For the few remaining spots in app.py using inline style= instead of CSS classes."""
    if theme == "dark":
        return {"accent": "#38BDF8", "subtext": "#94A3B8"}
    return {"accent": "#0369A1", "subtext": "#6B7280"}
