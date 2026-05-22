"""
styling.py - Custom CSS branding para SCM Prospector.

Paleta: charcoal + emerald. Vibe Linear/Notion sober B2B.
Aplicá apply_brand_styles() al inicio de cada page para layout consistente.
"""
import streamlit as st

BRAND_COLORS = {
    "primary": "#0F172A",       # Charcoal near-black — primary actions, headers
    "primary_dark": "#020617",  # Deeper black for hover / pressed
    "accent": "#10B981",        # Emerald — CTAs, highlights, success
    "accent_light": "#D1FAE5",  # Light emerald for backgrounds
    "success": "#10B981",       # Emerald (consolidated)
    "warning": "#F59E0B",       # Amber
    "danger": "#DC2626",        # Red
    "text_dark": "#0F172A",     # Charcoal main text
    "text_muted": "#64748B",    # Slate-500 captions
    "bg_light": "#F8FAFC",      # Slate-50 backgrounds
    "border": "#E2E8F0",        # Slate-200 borders
}


def apply_brand_styles():
    """Inject custom CSS para branding consistente en todas las pages."""
    st.markdown(
        f"""
        <style>
        /* ─── HEADERS ─── */
        h1 {{
            color: {BRAND_COLORS['primary']};
            font-weight: 700;
            border-bottom: 3px solid {BRAND_COLORS['accent']};
            padding-bottom: 8px;
        }}
        h2 {{
            color: {BRAND_COLORS['primary']};
            font-weight: 600;
        }}
        h3 {{
            color: {BRAND_COLORS['text_dark']};
            font-weight: 600;
        }}

        /* ─── BUTTONS ─── */
        .stButton > button {{
            background: linear-gradient(135deg, {BRAND_COLORS['primary']} 0%, {BRAND_COLORS['primary_dark']} 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        .stButton > button:hover {{
            background: {BRAND_COLORS['primary_dark']};
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.25);
            transform: translateY(-1px);
        }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, {BRAND_COLORS['accent']} 0%, #059669 100%);
        }}
        .stButton > button[kind="primary"]:hover {{
            background: #059669;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
        }}

        /* ─── METRICS ─── */
        [data-testid="stMetric"] {{
            background: linear-gradient(135deg, {BRAND_COLORS['bg_light']} 0%, white 100%);
            border-left: 4px solid {BRAND_COLORS['primary']};
            border-radius: 8px;
            padding: 16px 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        [data-testid="stMetricValue"] {{
            color: {BRAND_COLORS['primary']};
            font-weight: 700;
        }}
        [data-testid="stMetricLabel"] {{
            color: {BRAND_COLORS['text_muted']};
            font-weight: 500;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* ─── SIDEBAR ─── */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {BRAND_COLORS['bg_light']} 0%, white 100%);
            border-right: 1px solid {BRAND_COLORS['border']};
        }}
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
            color: {BRAND_COLORS['primary']};
            border-bottom: none;
        }}

        /* ─── INPUTS ─── */
        .stTextInput input, .stTextArea textarea, .stNumberInput input {{
            border: 1px solid {BRAND_COLORS['border']};
            border-radius: 6px;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{
            border-color: {BRAND_COLORS['accent']};
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
        }}

        /* ─── DATAFRAMES / TABLES ─── */
        [data-testid="stDataFrame"] {{
            border: 1px solid {BRAND_COLORS['border']};
            border-radius: 8px;
            overflow: hidden;
        }}

        /* ─── ALERTS ─── */
        .stAlert {{
            border-radius: 8px;
            border-left-width: 4px;
        }}

        /* ─── DIVIDERS ─── */
        hr {{
            border-color: {BRAND_COLORS['border']};
            margin: 1.5rem 0;
        }}

        /* ─── EXPANDERS ─── */
        [data-testid="stExpander"] {{
            border: 1px solid {BRAND_COLORS['border']};
            border-radius: 8px;
            background: white;
        }}

        /* ─── PROGRESS BAR ─── */
        [data-testid="stProgress"] > div > div {{
            background: linear-gradient(90deg, {BRAND_COLORS['primary']} 0%, {BRAND_COLORS['accent']} 100%);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand_header(title, subtitle=None, chip="BETA"):
    """Header consistente con título + chip de tier/status."""
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {BRAND_COLORS['primary']} 0%, {BRAND_COLORS['primary_dark']} 100%);
            color: white;
            padding: 24px 32px;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.25);
        ">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h1 style="color: white; margin: 0; border: none; padding: 0; font-size: 1.8rem;">
                        {title}
                    </h1>
                    {f'<p style="color: rgba(255,255,255,0.75); margin: 8px 0 0 0; font-size: 0.95rem;">{subtitle}</p>' if subtitle else ''}
                </div>
                <div style="
                    background: {BRAND_COLORS['accent']};
                    color: white;
                    padding: 6px 14px;
                    border-radius: 999px;
                    font-weight: 700;
                    font-size: 0.7rem;
                    letter-spacing: 1.5px;
                ">
                    {chip}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
