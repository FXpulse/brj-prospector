"""
app.py - SCM Prospector main entry / dashboard home.
"""
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.company_state import load_state as load_company_state, get_stats as get_company_stats
from lib.styling import apply_brand_styles, brand_header
from lib.auth import require_auth, render_user_chip
from lib.paths import get_tenant_searches_dir

try:
    from lib.hunter_enrich import hunter_credits_remaining
except Exception:
    hunter_credits_remaining = None

SCRIPT_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="SCM Prospector",
    page_icon="🎯",
    layout="wide",
)
apply_brand_styles()

# ── Auth gate ─────────────────────────────────────────────────────
user = require_auth()
render_user_chip(user)

brand_header(
    "SCM Prospector",
    f"Vacancy & Decision-Maker Intelligence for Staffing — Welcome back, {user['name'].split()[0]}",
)

# ─── Stats dashboard ────────────────────────────────────────────
st.divider()
st.subheader("📊 Dashboard")

# Tenant-scoped data
state = load_company_state(tenant=user["tenant"])
company_stats = get_company_stats(state)
searches_dir = get_tenant_searches_dir(user["tenant"])

total_searches = 0
job_searches = 0
companies_searches = 0
if searches_dir.exists():
    for f in searches_dir.glob("*.csv"):
        total_searches += 1
        if f.name.startswith("search_"):
            job_searches += 1
        elif f.name.startswith("companies_"):
            companies_searches += 1

hunter_remaining = None
hunter_total = 1000
if hunter_credits_remaining:
    try:
        hunter_remaining = hunter_credits_remaining()
    except Exception:
        hunter_remaining = None

# Top row — companies
c1, c2, c3, c4 = st.columns(4)
c1.metric("Companies tracked", company_stats["total_companies"])
c2.metric("Contacted", company_stats["contacted"])
c3.metric("Pending outreach", company_stats["in_db_not_contacted"])
c4.metric("With DM contact", company_stats["with_decision_maker"])

# Bottom row — activity + capacity
c5, c6, c7, c8 = st.columns(4)
c5.metric("Total runs", total_searches)
c6.metric("Job Search runs", job_searches)
c7.metric("Companies runs", companies_searches)
if hunter_remaining is not None:
    used = max(0, hunter_total - hunter_remaining)
    c8.metric("Hunter credits remaining", f"{hunter_remaining}/{hunter_total}", delta=-used, delta_color="off")
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

Find vacancies across multiple job boards (Indeed, LinkedIn, Glassdoor, Google).
Identifies each company's recruiter via enrichment API.

**Use for**: candidate prospecting + identifying external recruiters for networking.
        """
    )

with col_b:
    st.markdown(
        """
**🏢 Companies**

Detects companies with HIGH staffing demand (≥5 vacancies in key industries).
Finds HR Director / Plant Manager / Operations decision-maker.

**Use for**: prospecting potential CLIENTS — companies that USE staffing services.
        """
    )

# ─── Navigation ─────────────────────────────────────────────────
st.divider()
st.subheader("📚 Navigation")

st.markdown(
    """
| Page | Purpose |
|---|---|
| 🔍 **Job Search** | Search vacancies + recruiter contacts (Pipeline A) |
| 🏢 **Companies** | Find companies using staffing + decision-makers (Pipeline B) |
| 📊 **History** | View/download all past searches |
| 🗄️ **Database** | Browse + edit all tracked companies, mark as contacted |
"""
)

st.divider()
st.caption(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · SCM Prospector · powered by Social Click Media")
