"""
5_Admin.py - Backoffice panel para admin tier.

Sections:
1. Tenants overview — todos los tenants con su usage del mes
2. User management — lista users con tier/tenant
3. System health — APIs configuradas, data folder sizes

Visible solo si user.tier == "admin". Otros tiers ven "Access denied".
"""
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

st.set_page_config(page_title="Admin - SCM Prospector", page_icon="🛡️", layout="wide")
from lib.styling import apply_brand_styles, brand_header
from lib.auth import require_auth, render_user_chip
from lib.tiers import TIERS, get_tier_config
from lib.usage import list_all_tenants_usage, get_usage_history
from lib.paths import CLIENTS_DIR, SHARED_DIR, DATA_DIR
from lib.config_loader import load_config

apply_brand_styles()
user = require_auth()
render_user_chip(user)

# ── Access gate — admin only ─────────────────────────────────────
if user["tier"] != "admin":
    brand_header("🛡️ Admin Panel", "Access restricted")
    st.error(f"⛔ Access denied. This page is for admin tier only. Your tier: **{user['tier']}**")
    st.caption("If you need admin access, contact hello@theprospector.io")
    st.stop()

brand_header(
    "🛡️ Admin Panel",
    "Monitor tenants, users, system health — SCM Prospector",
)

cfg = load_config()
auth_cfg = cfg.get("auth", {})


# ─── Section 1: Tenants Overview ────────────────────────────────
st.subheader("🏢 Tenants — this month's activity")

tenants_usage = list_all_tenants_usage()

if not tenants_usage:
    st.info("No tenant data yet. Tenants are auto-created when users start running searches.")
else:
    # Enrich with tier info from auth config
    rows = []
    for tu in tenants_usage:
        # Find users in this tenant
        tenant_users = [
            (email, data)
            for email, data in (auth_cfg.get("users") or {}).items()
            if data.get("tenant") == tu["tenant"]
        ]
        # Pick the highest tier of users in this tenant for display
        tiers_in_tenant = [data.get("tier", "starter") for _, data in tenant_users]
        # Tier hierarchy
        tier_priority = {"admin": 4, "custom": 3, "pro": 2, "starter": 1}
        primary_tier = max(tiers_in_tenant, key=lambda t: tier_priority.get(t, 0)) if tiers_in_tenant else "—"

        tier_cfg = get_tier_config(primary_tier) if primary_tier != "—" else {}
        email_limit = tier_cfg.get("monthly_emails", 0)
        phone_limit = tier_cfg.get("monthly_phones", 0)

        rows.append({
            "Tenant": tu["tenant"].upper(),
            "Tier": primary_tier.upper() if primary_tier != "—" else "—",
            "Users": len(tenant_users),
            "Emails used": f"{tu.get('emails', 0)} / {email_limit if email_limit < 999_999 else '∞'}",
            "Phones used": f"{tu.get('phones', 0)} / {phone_limit if phone_limit < 999_999 else '∞'}",
            "Searches": tu.get("searches", 0),
            "Last activity": tu.get("last_use", "—") or "—",
        })

    df_tenants = pd.DataFrame(rows)
    st.dataframe(
        df_tenants,
        use_container_width=True,
        hide_index=True,
    )

    # Top-line metrics
    total_emails = sum(tu.get("emails", 0) for tu in tenants_usage)
    total_phones = sum(tu.get("phones", 0) for tu in tenants_usage)
    total_searches = sum(tu.get("searches", 0) for tu in tenants_usage)
    active_tenants = sum(1 for tu in tenants_usage if tu.get("searches", 0) > 0)

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active tenants", active_tenants)
    c2.metric("Total emails this month", total_emails)
    c3.metric("Total phones this month", total_phones)
    c4.metric("Total searches this month", total_searches)

    # ─── Per-tenant drill-down ────────────────────────────────────
    st.divider()
    st.subheader("🔍 Tenant drill-down")

    tenant_names = [tu["tenant"] for tu in tenants_usage]
    selected_tenant = st.selectbox("Select tenant", options=tenant_names)

    if selected_tenant:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Historical usage (last 6 months)**")
            history = get_usage_history(tenant=selected_tenant, months=6)
            if history:
                hist_df = pd.DataFrame([
                    {
                        "Month": m,
                        "Emails": data.get("emails", 0),
                        "Phones": data.get("phones", 0),
                        "Searches": data.get("searches", 0),
                    }
                    for m, data in history
                ])
                st.dataframe(hist_df, use_container_width=True, hide_index=True)
            else:
                st.caption("No historical data yet.")

        with col_b:
            st.markdown("**Tenant data folder**")
            tenant_dir = CLIENTS_DIR / selected_tenant
            if tenant_dir.exists():
                # Count files
                searches_dir = tenant_dir / "searches"
                n_searches = len(list(searches_dir.glob("*.csv"))) if searches_dir.exists() else 0
                state_file = tenant_dir / "company_state.json"
                state_size_kb = round(state_file.stat().st_size / 1024, 1) if state_file.exists() else 0
                folder_size_mb = sum(f.stat().st_size for f in tenant_dir.rglob("*") if f.is_file()) / 1024 / 1024

                st.write(f"**Path**: `{tenant_dir.relative_to(DATA_DIR.parent)}`")
                st.write(f"**Search CSVs**: {n_searches}")
                st.write(f"**State file**: {state_size_kb} KB")
                st.write(f"**Total folder size**: {round(folder_size_mb, 2)} MB")
            else:
                st.caption("Folder does not exist yet.")


# ─── Section 2: User Management ─────────────────────────────────
st.divider()
st.subheader("👥 Users")

users = auth_cfg.get("users") or {}
if not users:
    st.warning("No users configured. Add users to auth.users in config.json or Streamlit Secrets.")
else:
    user_rows = []
    for email, data in users.items():
        user_rows.append({
            "Email": email,
            "Name": data.get("name", "—"),
            "Tenant": data.get("tenant", "—").upper(),
            "Tier": data.get("tier", "—").upper(),
        })
    df_users = pd.DataFrame(user_rows)
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.caption(
        "ℹ️ User management is currently read-only via this UI. "
        "To add/remove/modify users: edit `config.json` (local) or "
        "Streamlit Secrets (cloud) → restart app. "
        "Generate password hashes with `python scripts/hash_password.py`."
    )

# ─── Section 3: System Health ───────────────────────────────────
st.divider()
st.subheader("⚙️ System Health")

col1, col2, col3, col4 = st.columns(4)

# Hunter API
hunter_ok = bool(cfg.get("hunter", {}).get("api_key", "").strip() and not cfg.get("hunter", {}).get("api_key", "").startswith("PASTE"))
try:
    from lib.hunter_enrich import hunter_credits_remaining
    hunter_remaining = hunter_credits_remaining(cfg) if hunter_ok else 0
    hunter_total = cfg.get("hunter", {}).get("monthly_limit", 1000)
except Exception:
    hunter_remaining = 0
    hunter_total = 1000

col1.metric(
    "Hunter API",
    "✓ Active" if hunter_ok else "⚠️ Not configured",
    delta=f"{hunter_remaining}/{hunter_total} credits left" if hunter_ok else None,
    delta_color="off",
)

# Google CSE
has_cse = bool(cfg.get("google_cse", {}).get("cse_id", "").strip() and not cfg.get("google_cse", {}).get("cse_id", "").startswith("PASTE"))
col2.metric("Google CSE", "✓ Active" if has_cse else "⚠️ Not configured")

# GHL
has_ghl = bool(cfg.get("ghl", {}).get("pit", "").startswith("pit-"))
col3.metric("GHL API", "✓ Active" if has_ghl else "⚠️ Not configured")

# Apollo (placeholder — pending TOS verification + integration)
col4.metric("Apollo API", "🚧 Pending", delta="TOS check in progress")

# Data folder sizes
st.divider()
st.markdown("**Data storage**")

col_a, col_b, col_c = st.columns(3)

def folder_size_mb(p: Path) -> float:
    if not p.exists():
        return 0.0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1024 / 1024

total_data_mb = folder_size_mb(DATA_DIR)
clients_mb = folder_size_mb(CLIENTS_DIR)
shared_mb = folder_size_mb(SHARED_DIR)

col_a.metric("Total data/", f"{total_data_mb:.1f} MB")
col_b.metric("Tenant data (clients/)", f"{clients_mb:.1f} MB")
col_c.metric("Shared caches", f"{shared_mb:.1f} MB")

# ─── Footer ─────────────────────────────────────────────────────
st.divider()
st.caption(f"⏰ Admin view rendered {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · SCM Prospector · {user['email']}")
