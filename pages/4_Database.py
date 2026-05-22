"""
4_Database.py - Base de datos de todas las empresas tracked.

Muestra y permite editar el contenido de data/clients/<tenant>/company_state.json:
- Filtros por status, industry, has_dm, has_domain, search by name
- Tabla con info detallada
- Edit: marcar/desmarcar contacted, agregar notas
- Bulk: marcar selected, delete
- Export CSV
"""
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.company_state import (
    load_state,
    save_state,
    mark_as_contacted,
    normalize_company_key,
    get_stats,
)

st.set_page_config(page_title="Database - SCM Prospector", page_icon="🗄️", layout="wide")
from lib.styling import apply_brand_styles, brand_header
from lib.auth import require_auth, render_user_chip
apply_brand_styles()
user = require_auth()
render_user_chip(user)
brand_header(
    "🗄️ Database",
    "All tracked companies (cross-pipeline) — filter, edit, export",
)

# Load state
state = load_state()

if not state:
    st.info("Empty database. Run searches in Job Search or Companies to start tracking companies.")
    st.stop()

# ─── Convert state → DataFrame ─────────────────────────────────
records = []
for key, rec in state.items():
    dm = rec.get("decision_maker", {}) or {}
    records.append({
        "key": key,
        "company_name": rec.get("company_name", ""),
        "location": rec.get("location", ""),
        "status": "CONTACTED" if rec.get("contacted") else "IN_DB",
        "industries": ", ".join(rec.get("industries_seen", []) or []),
        "domain": rec.get("domain", ""),
        "dm_first_name": dm.get("first_name", ""),
        "dm_last_name": dm.get("last_name", ""),
        "dm_position": dm.get("position", ""),
        "dm_email": dm.get("email", ""),
        "dm_priority": dm.get("is_priority_role", False),
        "first_seen": rec.get("first_seen", ""),
        "last_seen": rec.get("last_seen", ""),
        "appearances": rec.get("appearances", 0),
        "max_vacancy_count": rec.get("max_vacancy_count", 0),
        "contact_date": rec.get("contact_date", "") or "",
        "notes": rec.get("notes", "") or "",
    })

df = pd.DataFrame(records)

# ─── Sidebar — filters + stats ─────────────────────────────────
with st.sidebar:
    st.header("📊 Database stats")
    stats = get_stats(state)
    st.metric("Total tracked", stats["total_companies"])
    col_a, col_b = st.columns(2)
    col_a.metric("Contacted", stats["contacted"])
    col_b.metric("Pending", stats["in_db_not_contacted"])
    st.caption(f"🌐 {stats['with_domain']} with domain · 🎯 {stats['with_decision_maker']} with DM")

    st.divider()
    st.header("🔎 Filters")

    status_options = ["IN_DB", "CONTACTED"]
    selected_statuses = st.multiselect("Status", options=status_options, default=["IN_DB"])

    all_industries = set()
    for r in records:
        for i in (r["industries"] or "").split(", "):
            if i.strip():
                all_industries.add(i.strip())
    selected_industries = st.multiselect("Industries", options=sorted(all_industries))

    has_dm_filter = st.selectbox(
        "Has decision-maker email",
        options=["Any", "Yes", "No"],
        index=0,
    )

    has_domain_filter = st.selectbox(
        "Has domain",
        options=["Any", "Yes", "No"],
        index=0,
    )

    priority_filter = st.selectbox(
        "Priority role (HR/Ops decision-maker)",
        options=["Any", "Only priority", "Only non-priority"],
        index=0,
    )

    name_search = st.text_input("Search by name", placeholder="ex: Acme, manufacturing...")

# ─── Apply filters ─────────────────────────────────────────────
filtered = df.copy()
if selected_statuses:
    filtered = filtered[filtered["status"].isin(selected_statuses)]
if selected_industries:
    pattern = "|".join(selected_industries)
    filtered = filtered[filtered["industries"].str.contains(pattern, case=False, na=False)]
if has_dm_filter == "Yes":
    filtered = filtered[filtered["dm_email"] != ""]
elif has_dm_filter == "No":
    filtered = filtered[filtered["dm_email"] == ""]
if has_domain_filter == "Yes":
    filtered = filtered[filtered["domain"] != ""]
elif has_domain_filter == "No":
    filtered = filtered[filtered["domain"] == ""]
if priority_filter == "Only priority":
    filtered = filtered[filtered["dm_priority"] == True]
elif priority_filter == "Only non-priority":
    filtered = filtered[(filtered["dm_priority"] == False) & (filtered["dm_email"] != "")]
if name_search:
    filtered = filtered[
        filtered["company_name"].str.contains(name_search, case=False, na=False)
        | filtered["domain"].str.contains(name_search, case=False, na=False)
    ]

# ─── Main display ──────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(f"📋 {len(filtered)} companies (of {len(df)} total)")
with col2:
    if len(filtered) > 0:
        csv_bytes = filtered.drop(columns=["key"]).to_csv(index=False).encode("utf-8")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "⬇ Export filtered CSV",
            data=csv_bytes,
            file_name=f"scm_database_{ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )

if filtered.empty:
    st.info("No companies match the filters. Adjust criteria in the sidebar.")
    st.stop()

# Display table
display_cols = [
    "status", "company_name", "location", "industries",
    "dm_first_name", "dm_last_name", "dm_position", "dm_email", "dm_priority",
    "domain", "max_vacancy_count", "appearances", "last_seen", "contact_date", "notes",
]
table_df = filtered[display_cols].copy()
table_df["last_seen"] = table_df["last_seen"].astype(str).str[:10]
table_df["contact_date"] = table_df["contact_date"].astype(str).str[:10]

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "status": st.column_config.TextColumn("Status"),
        "company_name": st.column_config.TextColumn("Company", width="medium"),
        "industries": st.column_config.TextColumn("Industries"),
        "dm_priority": st.column_config.CheckboxColumn("Priority"),
        "dm_email": st.column_config.TextColumn("Email"),
        "max_vacancy_count": st.column_config.NumberColumn("Max vacancies"),
        "appearances": st.column_config.NumberColumn("Times seen"),
        "last_seen": st.column_config.TextColumn("Last seen"),
        "contact_date": st.column_config.TextColumn("Contacted"),
    },
)

# ─── Bulk actions ──────────────────────────────────────────────
st.divider()
st.subheader("⚙️ Bulk actions on filtered")

col_action1, col_action2, col_action3 = st.columns(3)

with col_action1:
    if st.button(f"✓ Mark {len(filtered)} as contacted", use_container_width=True):
        for _, row in filtered.iterrows():
            state = mark_as_contacted(state, row["company_name"], row["location"], note="Bulk from Database")
        save_state(state)
        st.success(f"✓ {len(filtered)} marked as contacted.")
        st.caption("Refresh the page (F5) to see the change.")

with col_action2:
    if st.button(f"↩ Unmark contacted ({len(filtered)})", use_container_width=True):
        for _, row in filtered.iterrows():
            key = normalize_company_key(row["company_name"], row["location"])
            if key in state:
                state[key]["contacted"] = False
                state[key]["contact_date"] = None
        save_state(state)
        st.success(f"✓ {len(filtered)} unmarked.")
        st.caption("Refresh the page (F5).")

with col_action3:
    if st.button(f"🗑️ Delete {len(filtered)} from DB", use_container_width=True, help="⚠️ Permanent. Not reversible.", type="secondary"):
        keys_to_delete = filtered["key"].tolist()
        for k in keys_to_delete:
            state.pop(k, None)
        save_state(state)
        st.success(f"✓ {len(keys_to_delete)} permanently deleted.")
        st.caption("Refresh the page (F5).")

# ─── Single company detail viewer ──────────────────────────────
st.divider()
st.subheader("🔍 View company detail")

companies_for_select = filtered["company_name"].tolist()
selected = st.selectbox("Company", options=companies_for_select)

if selected:
    record_row = filtered[filtered["company_name"] == selected].iloc[0]
    key = record_row["key"]
    full_record = state.get(key, {})

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Identity**")
        st.write(f"**Company**: {full_record.get('company_name', '?')}")
        st.write(f"**Location**: {full_record.get('location', '?')}")
        st.write(f"**Domain**: {full_record.get('domain', '(none)')}")
        st.write(f"**Status**: {'CONTACTED' if full_record.get('contacted') else 'IN_DB'}")
        if full_record.get("contact_date"):
            st.write(f"**Contact date**: {full_record['contact_date']}")

        st.markdown("**Activity**")
        st.write(f"**First seen**: {full_record.get('first_seen', '?')}")
        st.write(f"**Last seen**: {full_record.get('last_seen', '?')}")
        st.write(f"**Appearances**: {full_record.get('appearances', 0)}")
        st.write(f"**Max vacancies**: {full_record.get('max_vacancy_count', 0)}")

    with col_r:
        st.markdown("**Decision-maker**")
        dm = full_record.get("decision_maker", {}) or {}
        if dm.get("email"):
            st.write(f"**Name**: {dm.get('first_name', '')} {dm.get('last_name', '')}")
            st.write(f"**Position**: {dm.get('position', '')}")
            st.write(f"**Email**: {dm.get('email', '')}")
            st.write(f"**Priority role**: {'✓' if dm.get('is_priority_role') else '✗'}")
            if dm.get("confidence"):
                st.write(f"**Hunter confidence**: {dm['confidence']}")
        else:
            st.write("_No decision-maker contact_")

        st.markdown("**Categorization**")
        st.write(f"**Industries seen**: {', '.join(full_record.get('industries_seen', []) or [])}")
        st.write(f"**Queries matched**: {len(full_record.get('queries_matched', []) or [])}")

    st.markdown("**Notes**")
    new_note = st.text_area(
        "Notes (manual)",
        value=full_record.get("notes", ""),
        height=80,
        key=f"notes_{key}",
    )
    if st.button("💾 Save notes", key=f"save_notes_{key}"):
        state[key]["notes"] = new_note
        save_state(state)
        st.success("Notes saved.")

    current_contacted = bool(full_record.get("contacted", False))
    new_contacted = st.checkbox(
        "Mark as contacted",
        value=current_contacted,
        key=f"contacted_{key}",
    )
    if new_contacted != current_contacted:
        state[key]["contacted"] = new_contacted
        state[key]["contact_date"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ") if new_contacted else None
        save_state(state)
        st.success(f"✓ {'Marked' if new_contacted else 'Unmarked'} contacted. Refresh the page.")
