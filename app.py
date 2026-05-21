"""
app.py - BRJ Prospector main entry / dashboard home.
"""
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.company_state import load_state as load_company_state, get_stats as get_company_stats
from lib.styling import apply_brand_styles, brand_header

try:
    from lib.hunter_enrich import hunter_credits_remaining
except Exception:
    hunter_credits_remaining = None

SCRIPT_DIR = Path(__file__).resolve().parent
SEARCHES_DIR = SCRIPT_DIR / "data" / "searches"

st.set_page_config(
    page_title="BRJ Prospector",
    page_icon="🎯",
    layout="wide",
)
apply_brand_styles()
brand_header(
    "BRJ Prospector",
    "Herramienta de prospecting multi-pipeline para Bilingual Recruiters Jacksonville",
)

# ─── Stats dashboard ────────────────────────────────────────────
st.divider()
st.subheader("📊 Dashboard")

state = load_company_state()
company_stats = get_company_stats(state)

# Count searches en history
total_searches = 0
job_searches = 0
companies_searches = 0
if SEARCHES_DIR.exists():
    for f in SEARCHES_DIR.glob("*.csv"):
        total_searches += 1
        if f.name.startswith("search_"):
            job_searches += 1
        elif f.name.startswith("companies_"):
            companies_searches += 1

# Hunter credits
hunter_remaining = None
hunter_total = 1000
if hunter_credits_remaining:
    try:
        hunter_remaining = hunter_credits_remaining()
    except Exception:
        hunter_remaining = None

# Top row — companies
c1, c2, c3, c4 = st.columns(4)
c1.metric("Empresas tracked", company_stats["total_companies"])
c2.metric("Contactadas", company_stats["contacted"])
c3.metric("Pendientes outreach", company_stats["in_db_not_contacted"])
c4.metric("Con DM contact", company_stats["with_decision_maker"])

# Bottom row — actividad + capacity
c5, c6, c7, c8 = st.columns(4)
c5.metric("Total runs", total_searches)
c6.metric("Job Search runs", job_searches)
c7.metric("Companies runs", companies_searches)
if hunter_remaining is not None:
    used = max(0, hunter_total - hunter_remaining)
    c8.metric("Hunter credits restantes", f"{hunter_remaining}/{hunter_total}", delta=-used, delta_color="off")
else:
    c8.metric("Hunter credits", "—")

# ─── Quick actions ──────────────────────────────────────────────
st.divider()
st.subheader("🚀 Quick start")

col_a, col_b = st.columns(2)
with col_a:
    st.markdown(
        """
**🔍 Job Search**

Encontrar vacantes en múltiples job boards (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google).
Identifica al recruiter de cada empresa via Hunter.io.

**Usá para**: prospectar candidatos para BRJ + identificar recruiters externos para networking.
        """
    )

with col_b:
    st.markdown(
        """
**🏢 Companies**

Detecta empresas con ALTA necesidad de staffing (≥5 vacantes en industrias clave).
Encuentra HR Director / Plant Manager / Operations decision-maker.

**Usá para**: prospectar CLIENTES potenciales — empresas que CONTRATAN staffing.
Foco: Manufacturing en NE Florida.
        """
    )

# ─── Navigation hints ───────────────────────────────────────────
st.divider()
st.subheader("📚 Navegación")

st.markdown(
    """
| Página | Para qué |
|---|---|
| 🔍 **Job Search** | Buscar vacantes + recruiter contacts (Pipeline A) |
| 🏢 **Companies** | Buscar empresas que usan staffing + decision-makers (Pipeline B) |
| 📊 **History** | Ver/descargar todas las búsquedas anteriores |
| 🗄️ **Database** | Browse + edit todas las empresas tracked, mark como contactadas |
"""
)

# ─── Status indicators ──────────────────────────────────────────
st.divider()
st.subheader("⚙️ Sistema")

try:
    from lib.config_loader import load_config
    cfg = load_config()
    has_hunter = bool(cfg.get("hunter", {}).get("api_key", "").strip() and not cfg.get("hunter", {}).get("api_key", "").startswith("PASTE"))
    has_cse = bool(cfg.get("google_cse", {}).get("cse_id", "").strip() and not cfg.get("google_cse", {}).get("cse_id", "").startswith("PASTE"))
except Exception:
    has_hunter = False
    has_cse = False

c1, c2, c3 = st.columns(3)
c1.metric("Hunter API", "✓ Activo" if has_hunter else "⚠️ No configurado")
c2.metric("Google CSE", "✓ Activo" if has_cse else "⚠️ No configurado")
c3.metric("Streamlit", f"Streamlit {st.__version__}")

if not has_hunter or not has_cse:
    st.warning(
        "Faltan credenciales. Configurá `config.json` local o Streamlit Secrets en cloud. "
        "Ver README para setup completo."
    )

st.caption(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · BRJ Prospector v1")
