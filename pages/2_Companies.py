"""
2_Companies.py - Pipeline B: detecta empresas con ALTA NECESIDAD de staffing.

Lógica:
1. Selecciona industria (Manufacturing, Hospitality, etc.)
2. Auto-genera 10-15 queries por industria
3. Run multi-query via JobSpy → empresas con N vacantes
4. Filtra empresas con >= min_vacancies (signal de staffing need)
5. Excluye staffing agencies + chains gigantes
6. Resuelve domains
7. Hunter lookup con priority de HR Director / Plant Manager / Operations
8. Output: ranked list de "high-staffing-need" prospects
"""
import sys
import time
from collections import defaultdict
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.jobspy_search import (
    run_search,
    filter_out_staffing_companies,
    SOURCE_NAMES,
)
from lib.industry_keywords import (
    get_industries,
    get_industry_config,
    get_queries_for_industry,
    get_decision_maker_roles,
    get_exclude_companies_for_industry,
)
from lib.domain_lookup import enrich_domains_in_dataframe
from lib.places_lookup import enrich_phones_in_dataframe
from lib.hunter_enrich import find_decision_maker_at_domain, hunter_credits_remaining, load_config as load_hunter_config
from lib.hunter_enrich import _load_json as _hunter_load_cache, _save_json as _hunter_save_cache, CACHE_FILE as HUNTER_CACHE_FILE
from lib.hunter_enrich import load_credits_state, save_credits_state
from lib.company_state import (
    load_state as load_company_state,
    save_state as save_company_state,
    get_company_status,
    upsert_company,
    mark_many_as_contacted,
    get_stats as get_company_stats,
)

st.set_page_config(page_title="Companies (Pipeline B) - SCM Prospector", page_icon="🏢", layout="wide")
from lib.styling import apply_brand_styles, brand_header
from lib.auth import require_auth, render_user_chip
apply_brand_styles()
user = require_auth()
render_user_chip(user)
brand_header(
    "🏢 Companies — Find companies that use staffing",
    "Detects companies with HIGH external staffing demand based on vacancy volume + type",
)

# ─── Sidebar: global stats ──────────────────────────────────────
with st.sidebar:
    st.header("📊 Global database")
    cs = load_company_state()
    stats = get_company_stats(cs)
    st.metric("Total companies tracked", stats["total_companies"])
    col_a, col_b = st.columns(2)
    col_a.metric("Contacted", stats["contacted"])
    col_b.metric("In DB (pending)", stats["in_db_not_contacted"])
    st.caption(f"🌐 {stats['with_domain']} with domain · 🎯 {stats['with_decision_maker']} with DM contact")

    st.divider()
    st.subheader("🔎 Display filters")
    hide_contacted = st.checkbox("Hide contacted (default)", value=True,
                                 help="Hides companies already marked as contacted. Recommended to avoid prospect overlap.")
    only_new = st.checkbox("Show only NEW", value=False,
                          help="Hides companies already in the DB. Useful to discover only new prospects.")

# ─── Industry selector + info ───────────────────────────────────
industries = get_industries()

col_ind, col_thresh, col_lookback = st.columns([2, 1, 1])
with col_ind:
    industry = st.selectbox(
        "Industry",
        options=industries,
        index=industries.index("Manufacturing") if "Manufacturing" in industries else 0,
        help="Each industry has 10-15 pre-built keywords. Manufacturing is the deepest (NE Florida case study).",
    )
    industry_cfg = get_industry_config(industry)
    st.caption(f"📍 {industry_cfg.get('description', '')}")
    st.caption(f"🌎 NE Florida density: {industry_cfg.get('ne_florida_density', '')}")

with col_thresh:
    min_vacancies = st.number_input(
        "Min vacancies",
        min_value=2,
        max_value=50,
        value=5,
        help="Companies with >= N open vacancies in the period. 5+ = strong external staffing signal.",
    )

with col_lookback:
    lookback = st.selectbox(
        "Lookback",
        options=["7d", "14d", "30d"],
        index=1,
        help="Search period. 14d is the sweet spot.",
    )

# ─── Locations ──────────────────────────────────────────────────
st.markdown("**Locations** (one per line)")
locations_text = st.text_area(
    "Locations",
    value="Jacksonville, FL\nOrange Park, FL\nSt Augustine, FL",
    height=80,
    label_visibility="collapsed",
)
locations = [l.strip() for l in locations_text.splitlines() if l.strip()]

# ─── Sources ────────────────────────────────────────────────────
st.markdown("**Sources**")
src_col1, src_col2, src_col3, src_col4 = st.columns(4)
with src_col1:
    use_indeed = st.checkbox("Indeed", value=True)
with src_col2:
    use_linkedin = st.checkbox("LinkedIn", value=True)
with src_col3:
    use_glassdoor = st.checkbox("Glassdoor", value=False)
with src_col4:
    use_google = st.checkbox("Google for Jobs", value=False)

sources = []
if use_indeed: sources.append("indeed")
if use_linkedin: sources.append("linkedin")
if use_glassdoor: sources.append("glassdoor")
if use_google: sources.append("google")

# ─── Queries preview ────────────────────────────────────────────
queries = get_queries_for_industry(industry)
with st.expander(f"📋 View the {len(queries)} queries that will run for {industry}"):
    cols = st.columns(3)
    for i, q in enumerate(queries):
        cols[i % 3].write(f"• {q}")

# ─── Options + Run ──────────────────────────────────────────────
col_hunter, col_max, col_run = st.columns([2, 1, 1])
with col_hunter:
    try:
        credits = hunter_credits_remaining()
    except Exception:
        credits = 0
    enrich_hunter = st.checkbox(
        f"🎯 Hunter HR enrichment (decision-maker lookup) — {credits} credits",
        value=True,
        disabled=credits <= 0,
        help="Searches for HR Director / Plant Manager / Operations at the end, only on companies with >= min_vacancies. Cache prevents re-queries.",
    )
with col_max:
    max_per_query = st.number_input("Max per query", min_value=10, max_value=100, value=30, step=10)
with col_run:
    st.markdown("&nbsp;")
    run = st.button("🚀 Find Companies", type="primary", use_container_width=True)

# ─── Restore previous results from session if available ────────
if "companies_results" in st.session_state and not run:
    st.info(
        "💾 Last run results loaded from session. "
        "Click 🚀 Find Companies to run again."
    )
    grouped_cached = st.session_state["companies_results"]
    last_run_info = st.session_state.get("companies_results_meta", {})

    st.divider()
    st.subheader(f"📋 {len(grouped_cached)} companies — {last_run_info.get('industry', '?')} (cached)")
    st.dataframe(grouped_cached, use_container_width=True, hide_index=True)

    csv_data_cached = grouped_cached.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Re-download CSV from last run",
        data=csv_data_cached,
        file_name=last_run_info.get("filename", "results.csv"),
        mime="text/csv",
    )

# ─── Run logic ──────────────────────────────────────────────────
if run:
    if not sources:
        st.error("Select at least 1 source.")
        st.stop()
    if not queries:
        st.error(f"No queries defined for {industry}.")
        st.stop()
    if not locations:
        st.error("Add at least 1 location.")
        st.stop()

    # Track search run
    try:
        from lib.usage import record_usage
        record_usage("searches", 1)
    except Exception:
        pass

    st.divider()

    total_runs = len(queries) * len(locations) * len(sources)
    st.info(f"⏱ Estimated: {len(queries)} queries × {len(locations)} locations × {len(sources)} sources = {total_runs} micro-searches. Takes 2-5 minutes.")

    all_jobs = []
    prog = st.progress(0, text=f"Starting — 0 / {len(queries)} queries")

    for qi, query in enumerate(queries):
        prog.progress(qi / len(queries), text=f"Query {qi+1}/{len(queries)}: {query[:40]}")
        try:
            df_q, errs = run_search(
                keywords=query,
                locations=locations,
                sources=sources,
                posted=lookback,
                results_per_query=max_per_query,
            )
            if not df_q.empty:
                df_q["search_query"] = query
                all_jobs.append(df_q)
        except Exception as e:
            st.warning(f"Query '{query[:40]}' failed: {e}")
        time.sleep(0.5)

    prog.empty()

    if not all_jobs:
        st.warning("No results from any query. Try a different industry or extend lookback period.")
        st.stop()

    df_all = pd.concat(all_jobs, ignore_index=True)
    st.success(f"✓ {len(df_all)} raw vacancies scraped across {len(queries)} queries")

    # Step 2: aggregate by company
    st.divider()
    st.subheader("📊 Aggregating by company...")

    df_all["company_clean"] = df_all["company"].fillna("").str.lower().str.strip()
    grouped = df_all.groupby("company_clean").agg(
        vacancy_count=("title", "count"),
        first_company_name=("company", "first"),
        first_company_url=("company_url", "first"),
        first_company_url_direct=("company_url_direct", "first"),
        first_emails=("emails", "first"),
        first_location=("location", "first"),
        sample_titles=("title", lambda x: " | ".join(x.dropna().unique()[:5])),
        first_date=("date_posted", "first"),
        queries_matched=("search_query", lambda x: ", ".join(sorted(set(x)))),
    ).reset_index()

    grouped = grouped.rename(columns={
        "first_company_name": "company",
        "first_company_url": "company_url",
        "first_company_url_direct": "company_url_direct",
        "first_emails": "emails",
        "first_location": "location",
        "first_date": "date_posted",
    })

    before_thresh = len(grouped)
    grouped = grouped[grouped["vacancy_count"] >= min_vacancies].copy()
    st.caption(f"Threshold filter ({min_vacancies}+ vacancies): {before_thresh} companies → {len(grouped)} with signal")

    if grouped.empty:
        st.warning(f"No companies with {min_vacancies}+ vacancies. Try lower threshold or extend lookback.")
        st.stop()

    grouped = grouped.sort_values("vacancy_count", ascending=False).reset_index(drop=True)

    # Step 3: filter staffing agencies + industry-specific excludes
    try:
        cfg = load_hunter_config()
        brj_cfg = cfg.get("brj_specific", {})
        kw_excl = brj_cfg.get("exclude_staffing_keywords", [])
        names_excl = brj_cfg.get("exclude_staffing_companies", []) + get_exclude_companies_for_industry(industry)
        before_filter = len(grouped)
        grouped, excluded_count, sample = filter_out_staffing_companies(grouped, kw_excl, names_excl)
        if excluded_count > 0:
            with st.expander(f"🚫 Excluded {excluded_count} companies (staffing agencies + mega chains)"):
                for s in sample:
                    st.write(f"  • {s}")
        st.caption(f"Staffing+chains filter: {before_filter} → {len(grouped)} relevant prospects")
    except Exception as e:
        st.warning(f"Filter failed (non-fatal): {e}")
        cfg = {}

    if grouped.empty:
        st.warning("Nothing remained after filters. Review thresholds.")
        st.stop()

    # Step 4: domain enrichment
    st.divider()
    st.subheader("🌐 Resolving real domains...")

    google_cse_ok = (
        cfg.get("google_cse", {}).get("cse_id", "").strip()
        and not cfg.get("google_cse", {}).get("cse_id", "").startswith("PASTE")
    )

    dprogress = st.progress(0, text="...")
    def dcb(i, total, company, domain, source):
        label = f"{i}/{total} • {str(company or '?')[:30]}"
        if domain:
            label += f" → {domain} [{source or '?'}]"
        dprogress.progress(i / total, text=label[:90])

    grouped = enrich_domains_in_dataframe(
        grouped, cfg,
        use_indeed_scrape=True,
        use_google_search=google_cse_ok,
        progress_cb=dcb,
    )
    dprogress.empty()

    domains_found = grouped["company_domain"].notna().sum()
    st.success(f"✓ Domains: {domains_found}/{len(grouped)} resolved")

    # Step 4b: Company phones via Google Places
    st.divider()
    st.subheader("📞 Resolving company phones...")

    pprogress = st.progress(0, text="Starting...")
    def pcb(i, total, company, phone):
        label = f"{i}/{total} • {str(company)[:35]}"
        if phone:
            label += f" → {phone}"
        pprogress.progress(i / total, text=label[:90])

    grouped = enrich_phones_in_dataframe(grouped, cfg, progress_cb=pcb)
    pprogress.empty()

    phones_found = sum(1 for p in grouped.get("company_phone", []) if p)
    st.success(f"✓ Phones: {phones_found}/{len(grouped)} found via Google Places")

    # Step 5: Hunter HR enrichment
    if enrich_hunter and domains_found > 0:
        st.divider()
        st.subheader("🎯 Hunter — searching HR decision-makers")

        priority_roles = get_decision_maker_roles(industry)
        st.caption(f"Prioritizing roles for {industry}: {', '.join(priority_roles[:5])}…")

        credits_state = load_credits_state()
        hunter_cache = _hunter_load_cache(HUNTER_CACHE_FILE, {})

        hprogress = st.progress(0, text="...")
        decision_makers = []

        for i, row in enumerate(grouped.itertuples(index=False)):
            domain = getattr(row, "company_domain", None)
            company_raw = getattr(row, "company", None)
            company = str(company_raw) if company_raw and str(company_raw).lower() != "nan" else "?"

            if domain and (isinstance(domain, float) or str(domain).lower() == "nan"):
                domain = None

            if not domain:
                decision_makers.append({})
                hprogress.progress((i + 1) / len(grouped), text=f"{i+1}/{len(grouped)} • {company[:30]} • (no domain)")
                continue

            cache_key = f"{domain}__pipelineB"
            if cache_key in hunter_cache:
                result = {**hunter_cache[cache_key], "from_cache": True}
            else:
                # Global Hunter API limit check
                if credits_state.get("used", 0) >= cfg.get("hunter", {}).get("monthly_limit", 1000):
                    decision_makers.append({"error": "credits exhausted"})
                    continue
                # Per-tenant tier limit check
                try:
                    from lib.usage import can_consume
                    if not can_consume("emails", user["tier"], 1, tenant=user["tenant"]):
                        decision_makers.append({"error": "tier_limit_reached"})
                        continue
                except Exception:
                    pass
                result = find_decision_maker_at_domain(domain, cfg, priority_roles=priority_roles)
                if not result.get("error"):
                    credits_state["used"] = credits_state.get("used", 0) + 1
                    try:
                        from lib.usage import record_usage
                        record_usage("emails", 1)
                    except Exception:
                        pass
                hunter_cache[cache_key] = result

            decision_makers.append(result)
            label = f"{i+1}/{len(grouped)} • {str(company)[:30]}"
            if result.get("email"):
                fn = result.get("first_name") or ""
                ln = result.get("last_name") or ""
                pos = (result.get("position") or "")[:30]
                label += f" → {fn} {ln} ({pos})"
            hprogress.progress((i + 1) / len(grouped), text=label[:100])
            if not result.get("from_cache") and not result.get("error"):
                time.sleep(0.1)

        save_credits_state(credits_state)
        _hunter_save_cache(HUNTER_CACHE_FILE, hunter_cache)

        grouped["dm_first_name"] = [d.get("first_name", "") for d in decision_makers]
        grouped["dm_last_name"] = [d.get("last_name", "") for d in decision_makers]
        grouped["dm_position"] = [d.get("position", "") for d in decision_makers]
        grouped["dm_email"] = [d.get("email", "") for d in decision_makers]
        grouped["dm_phone"] = [d.get("phone", "") for d in decision_makers]
        grouped["dm_is_priority_role"] = [d.get("is_priority_role", False) for d in decision_makers]
        grouped["dm_confidence"] = [d.get("confidence", "") for d in decision_makers]

        hprogress.empty()
        with_dm = sum(1 for d in decision_makers if d.get("email"))
        priority_dm = sum(1 for d in decision_makers if d.get("is_priority_role"))
        blocked_by_tier = sum(1 for d in decision_makers if d.get("error") == "tier_limit_reached")

        if blocked_by_tier > 0:
            st.warning(
                f"⚠️ **Tier limit reached** — {blocked_by_tier} companies were not enriched because "
                f"your {user['tier'].upper()} tier email quota is exhausted this month. "
                f"Email hello@theprospector.io to request a top-up, or wait until next month."
            )

        st.success(f"✓ Hunter: {with_dm}/{len(grouped)} with decision-maker, {priority_dm} in priority role (HR/Ops/GM)")

    # ─── State sync — classify companies: NEW / IN_DB / CONTACTED ───
    company_state = load_company_state()
    statuses = []
    for _, row in grouped.iterrows():
        st_info = get_company_status(company_state, row.get("company", ""), row.get("location", ""))
        statuses.append(st_info["status"])
    grouped["status"] = statuses

    for _, row in grouped.iterrows():
        dm_data = {}
        if enrich_hunter and row.get("dm_email"):
            dm_data = {
                "first_name": row.get("dm_first_name", ""),
                "last_name": row.get("dm_last_name", ""),
                "position": row.get("dm_position", ""),
                "email": row.get("dm_email", ""),
                "is_priority_role": bool(row.get("dm_is_priority_role", False)),
            }
        upsert_company(
            company_state,
            company_name=row.get("company", ""),
            location=row.get("location", ""),
            domain=row.get("company_domain", "") or None,
            decision_maker=dm_data or None,
            industries=[industry],
            queries_matched=str(row.get("queries_matched", "")).split(", "),
            vacancy_count=int(row.get("vacancy_count", 0)),
        )
    save_company_state(company_state)

    # ─── Apply user filters ──────────
    before_filter = len(grouped)
    if hide_contacted:
        grouped = grouped[grouped["status"] != "CONTACTED"]
    if only_new:
        grouped = grouped[grouped["status"] == "NEW"]

    filter_caption = f"UI filters: {before_filter} → {len(grouped)}"
    if hide_contacted:
        filter_caption += f" (hiding {sum(1 for s in statuses if s == 'CONTACTED')} already contacted)"
    if only_new:
        filter_caption += f" (only NEW)"
    st.caption(filter_caption)

    if grouped.empty:
        st.info("No companies to show with current filters. Uncheck filters or change the search.")
        st.stop()

    # ─── Final table ────────────────────────────────────────────
    st.divider()
    st.subheader(f"📋 {len(grouped)} companies with staffing signal — {industry}")

    display_cols = ["status", "company", "vacancy_count", "company_phone", "sample_titles", "location"]
    if enrich_hunter:
        display_cols.extend([
            "dm_first_name", "dm_last_name", "dm_position",
            "dm_email", "dm_phone", "dm_is_priority_role",
        ])
    display_cols.extend(["company_domain", "queries_matched", "domain_source", "company_url"])
    avail = [c for c in display_cols if c in grouped.columns]
    table = grouped[avail].copy()

    if "sample_titles" in table.columns:
        table["sample_titles"] = table["sample_titles"].str[:120]

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "status": st.column_config.TextColumn("Status", help="NEW=first time. IN_DB=already tracked. CONTACTED=already contacted (filtered by default)."),
            "vacancy_count": st.column_config.NumberColumn("Vacancies", help="Total vacancies in the period"),
            "company_phone": st.column_config.TextColumn("📞 Company phone", help="Company general phone via Google Places"),
            "sample_titles": st.column_config.TextColumn("Sample titles"),
            "queries_matched": st.column_config.TextColumn("Matched queries"),
            "dm_first_name": st.column_config.TextColumn("Decision-maker name"),
            "dm_position": st.column_config.TextColumn("Position"),
            "dm_email": st.column_config.TextColumn("Email"),
            "dm_phone": st.column_config.TextColumn("📱 DM direct phone", help="Decision-maker direct phone (rare — Hunter only returns it sometimes)"),
            "dm_is_priority_role": st.column_config.CheckboxColumn("Priority role"),
            "company_url": st.column_config.LinkColumn("Indeed/JB"),
        },
    )

    # ─── Bulk action: mark as contacted ────────────────────
    st.divider()
    st.subheader("📌 Bulk actions")

    col_action, col_note = st.columns([1, 2])
    with col_action:
        if st.button(f"✓ Mark all {len(grouped)} as contacted", use_container_width=True):
            items = [(row["company"], row.get("location", "")) for _, row in grouped.iterrows()]
            company_state = load_company_state()
            company_state = mark_many_as_contacted(company_state, items, note=f"Bulk marked from {industry} run {datetime.now().strftime('%Y-%m-%d')}")
            save_company_state(company_state)
            st.success(f"✓ {len(items)} companies marked as contacted. Future searches will hide them.")
            st.caption("Refresh the page to see the filter applied.")
    with col_note:
        st.caption(
            "💡 **Recommended workflow**: after doing manual outreach to companies on this list "
            "(LinkedIn DMs, emails, calls), click this button. Future searches will skip them "
            "automatically. If you need to see them again, uncheck 'Hide contacted' in the sidebar."
        )

    # Stats
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies (prospects)", len(grouped))
    c2.metric("Total vacancies", int(grouped["vacancy_count"].sum()))
    if enrich_hunter:
        with_dm = sum(1 for x in grouped.get("dm_email", []) if x)
        c3.metric("With HR contact", with_dm)
        prio = sum(1 for x in grouped.get("dm_is_priority_role", []) if x)
        c4.metric("Priority role", prio)

    # Download
    csv_data = grouped.to_csv(index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "⬇ Download CSV (all columns)",
        data=csv_data,
        file_name=f"scm_companies_{industry.replace(' ', '_')}_{ts}.csv",
        mime="text/csv",
    )

    # Save to history (tenant-scoped)
    from lib.paths import get_tenant_searches_dir
    history_dir = get_tenant_searches_dir(user["tenant"])
    csv_filename = f"companies_{ts}_{industry.replace(' ', '_')}.csv"
    grouped.to_csv(history_dir / csv_filename, index=False)
    st.caption(f"✓ Run saved to tenant history ({user['tenant']}) — {csv_filename}")

    st.session_state["companies_results"] = grouped
    st.session_state["companies_results_meta"] = {
        "industry": industry,
        "filename": f"scm_companies_{industry.replace(' ', '_')}_{ts}.csv",
        "timestamp": ts,
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
