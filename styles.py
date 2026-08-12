FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500&display=swap');"

CATEGORY_PILL_CLASS = {
    "Everyday / Casual": "pill-everyday",
    "Sports & Training": "pill-sports",
    "Medical & Comfort": "pill-medical",
}


def _build_css(*, bg, card_bg, card_border, text, subtext, heading, accent, accent_hover,
                guide_bg, guide_border, pill_everyday_bg, pill_everyday_text,
                pill_sports_bg, pill_sports_text, pill_medical_bg, pill_medical_text,
                badge_ok_bg, badge_ok_text, badge_warn_bg, badge_warn_text,
                track_bg, disclaimer_bg, disclaimer_text, app_bg):
    return f"""
    <style>
    {FONT_IMPORT}

    .stApp {{ background-color: {app_bg}; }}
    html, body, [class*="css"]  {{ font-family: 'Inter', sans-serif; color: {text}; }}

    .hero {{
        background-color: {bg};
        border: 1px solid {card_border};
        border-radius: 16px;
        padding: 26px 24px;
        text-align: center;
        margin-bottom: 22px;
    }}
    .hero-title {{
        font-family: 'Poppins', sans-serif;
        font-size: 2.1rem;
        font-weight: 700;
        color: {heading};
        margin: 0;
    }}
    .hero-subtitle {{ color: {subtext}; font-size: 1.02rem; margin-top: 6px; }}

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
        transition: border-color 0.2s ease;
    }}
    .rec-card:hover {{ border-color: {accent}; }}
    .rec-card strong {{ font-size: 1.15rem; color: {accent}; font-family: 'Poppins', sans-serif; }}

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
