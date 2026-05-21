"""
styling.py - Custom CSS branding para BRJ Prospector.

Aplicá apply_brand_styles() al inicio de cada page para layout consistente.
"""
import streamlit as st

# Paleta BRJ
BRAND_COLORS = {
    "primary": "#1E4D8C",       # Navy — primary actions, headers
    "primary_dark": "#143866",  # Hover / pressed states
    "accent": "#E89923",        # Gold — highlights, important callouts
    "accent_light": "#F5C470",  # Lighter gold for backgrounds
    "success": "#16A34A",       # Green — positive metrics
    "warning": "#F59E0B",       # Amber — caution
    "danger": "#DC2626",        # Red — errors
    "text_dark": "#1A2238",     # Main text
    "text_muted": "#6B7280",    # Captions, secondary text
    "bg_light": "#F5F7FA",      # Light backgrounds
    "border": "#E5E7EB",        # Subtle borders
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
            box-shadow: 0 4px 12px rgba(30, 77, 140, 0.3);
            transform: translateY(-1px);
        }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, {BRAND_COLORS['accent']} 0%, #D88615 100%);
        }}
        .stButton > button[kind="primary"]:hover {{
            background: #D88615;
            box-shadow: 0 4px 12px rgba(232, 153, 35, 0.4);
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
            border-color: {BRAND_COLORS['primary']};
            box-shadow: 0 0 0 3px rgba(30, 77, 140, 0.1);
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


def brand_header(title, subtitle=None):
    """Header consistente con logo BRJ + título."""
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {BRAND_COLORS['primary']} 0%, {BRAND_COLORS['primary_dark']} 100%);
            color: white;
            padding: 24px 32px;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 4px 12px rgba(30, 77, 140, 0.2);
        ">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h1 style="color: white; margin: 0; border: none; padding: 0; font-size: 1.8rem;">
                        {title}
                    </h1>
                    {f'<p style="color: rgba(255,255,255,0.85); margin: 8px 0 0 0; font-size: 0.95rem;">{subtitle}</p>' if subtitle else ''}
                </div>
                <div style="
                    background: {BRAND_COLORS['accent']};
                    color: {BRAND_COLORS['primary_dark']};
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 0.9rem;
                    letter-spacing: 1px;
                ">
                    BRJ
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
