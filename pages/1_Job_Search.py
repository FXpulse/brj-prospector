"""
1_Job_Search.py - Página de búsqueda de vacantes multi-source.
"""
import sys
import time
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

# Add parent to path para importar lib
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.jobspy_search import (
    run_search,
    filter_by_keywords,
    filter_out_staffing_companies,
    dedup_by_company,
    SOURCE_NAMES,
    HOURS_LOOKUP,
)
from lib.domain_lookup import enrich_domains_in_dataframe
from lib.hunter_enrich import (
    enrich_dataframe as hunter_enrich,
    hunter_credits_remaining,
    load_config as load_hunter_config,
)

st.set_page_config(page_title="Job Search - SCM Prospector", page_icon="🔍", layout="wide")
from lib.styling import apply_brand_styles, brand_header
from lib.auth import require_auth, render_user_chip
apply_brand_styles()
user = require_auth()
render_user_chip(user)
brand_header("🔍 Job Search", "Search vacancies across multiple job boards simultaneously")

# ─── Search form ────────────────────────────────────────────────
with st.form("search_form"):
    col_kw, col_count = st.columns([3, 1])
    with col_kw:
        keywords = st.text_input(
            "Keywords",
            value="warehouse worker",
            help="Job title or keywords your recruiters look for. Ex: 'warehouse forklift', 'RN nurse bilingual', 'driver CDL'",
        )
    with col_count:
        results_per_query = st.number_input(
            "Max per search",
            min_value=10,
            max_value=200,
            value=50,
            step=10,
            help="Max vacancies per (location × source)",
        )

    st.markdown("**Locations** — one or more cities/ZIPs (one per line)")
    locations_text = st.text_area(
        "Locations",
        value="Jacksonville, FL\nOrange Park, FL",
        height=100,
        help="One location per line. Ex: 'Jacksonville, FL' or '32256'. Empty = nationwide search.",
        label_visibility="collapsed",
    )
    locations = [l.strip() for l in locations_text.splitlines() if l.strip()]

    col_src, col_post, col_jobtype = st.columns(3)
    with col_src:
        st.markdown("**Sources**")
        sources_selected = []
        for code, label in [
            ("indeed", "Indeed"),
            ("linkedin", "LinkedIn"),
            ("zip_recruiter", "ZipRecruiter"),
            ("glassdoor", "Glassdoor"),
            ("google", "Google for Jobs"),
        ]:
            if st.checkbox(label, value=(code in ["indeed", "linkedin", "zip_recruiter"]), key=f"src_{code}"):
                sources_selected.append(code)

    with col_post:
        st.markdown("**Posted recently**")
        posted = st.radio(
            "Posted recently",
            options=["24h", "48h", "7d", "14d", "30d"],
            index=2,
            label_visibility="collapsed",
        )

    with col_jobtype:
        st.markdown("**Job type (optional)**")
        job_type_choice = st.selectbox(
            "Job type",
            options=["Any", "fulltime", "parttime", "contract", "internship"],
            label_visibility="collapsed",
        )
        job_type = None if job_type_choice == "Any" else job_type_choice

    st.markdown("**Optional filters** (post-scrape, client-side)")
    col_must, col_not = st.columns(2)
    with col_must:
        must_contain_text = st.text_input(
            "Title/description must contain (at least one)",
            placeholder="bilingual, spanish, portuguese",
            help="Comma-separated. Additional filter. Empty = no filter.",
        )
    with col_not:
        must_not_text = st.text_input(
            "Title/description must NOT contain (any)",
            placeholder="senior, manager, executive",
            help="Comma-separated. Excludes matches.",
        )

    col_dedup, col_exclude, col_hunter, col_run = st.columns([2, 2, 2, 1])
    with col_dedup:
        dedup_companies = st.checkbox(
            "Dedup by company",
            value=True,
            help="1 row per company, groups vacancies together",
        )
    with col_exclude:
        exclude_staffing = st.checkbox(
            "🚫 Exclude staffing agencies",
            value=True,
            help="Filters competitors (Adecco, Robert Half, etc. + any company with 'staffing', 'recruiting' in the name). Protects Hunter credits.",
        )
    with col_hunter:
        try:
            credits_remaining = hunter_credits_remaining()
            hunter_label = f"Hunter enrich (recruiter lookup) — {credits_remaining} credits left"
        except Exception:
            credits_remaining = 0
            hunter_label = "Hunter enrich (recruiter lookup) — config error"
        enrich_with_hunter = st.checkbox(
            hunter_label,
            value=False,
            disabled=credits_remaining <= 0,
            help="Finds each company's recruiter/HR via Hunter.io. Prioritizes roles: Recruiter, HR Manager, Talent Acquisition.",
        )
    with col_run:
        st.markdown("&nbsp;")
        submit = st.form_submit_button("🚀 Run Search", type="primary", use_container_width=True)

# ─── Restore last results from session if available ───────────
if "jobs_results" in st.session_state and not submit:
    st.info(
        "💾 Last Job Search results loaded from session. "
        "Click 🚀 Run Search to run again."
    )
    cached_df = st.session_state["jobs_results"]
    cached_meta = st.session_state.get("jobs_results_meta", {})

    st.divider()
    st.subheader(f"📋 {len(cached_df)} {'companies' if cached_meta.get('dedup') else 'vacancies'} (cached)")
    st.dataframe(cached_df, use_container_width=True, hide_index=True)

    csv_cached = cached_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Re-download CSV from last run",
        data=csv_cached,
        file_name=cached_meta.get("filename", "results.csv"),
        mime="text/csv",
    )

# ─── Run search ─────────────────────────────────────────────────
if submit:
    if not keywords.strip():
        st.error("Keywords cannot be empty.")
        st.stop()
    if not sources_selected:
        st.error("Select at least 1 source.")
        st.stop()

    st.divider()

    with st.status(f"Scraping {len(sources_selected)} sources × {len(locations) or 1} locations...", expanded=True) as status:
        st.write(f"- Keywords: `{keywords}`")
        st.write(f"- Sources: {', '.join(sources_selected)}")
        st.write(f"- Locations: {locations or ['(global)']}")
        st.write(f"- Posted: {posted}")
        st.write(f"- Job type: {job_type or 'any'}")
        st.write(f"- Max per query: {results_per_query}")

        try:
            t_start = time.time()
            df, errors = run_search(
                keywords=keywords,
                locations=locations or [""],
                sources=sources_selected,
                posted=posted,
                results_per_query=results_per_query,
                job_type=job_type,
            )
            elapsed = time.time() - t_start
            status.update(label=f"✓ Search complete in {elapsed:.1f}s — {len(df)} jobs", state="complete")
        except Exception as e:
            status.update(label=f"✗ Search error: {e}", state="error")
            st.exception(e)
            st.stop()

        if errors:
            with st.expander(f"⚠️ {len(errors)} location(s) had errors"):
                for err in errors:
                    st.write(f"- `{err['location']}`: {err['error']}")

    if df.empty:
        st.warning("No results. Try broader keywords/locations.")
        st.stop()

    # Apply client-side filters
    must_contain = [s.strip() for s in must_contain_text.split(",") if s.strip()]
    must_not = [s.strip() for s in must_not_text.split(",") if s.strip()]
    if must_contain or must_not:
        before = len(df)
        df = filter_by_keywords(df, must_contain=must_contain or None, must_not_contain=must_not or None)
        st.caption(f"Filters applied: {before} → {len(df)} jobs")

    # Optional dedup
    if dedup_companies:
        before = len(df)
        df_display = dedup_by_company(df)
        st.caption(f"Dedup by company: {before} jobs → {len(df_display)} unique companies")
    else:
        df_display = df

    # ─── Exclude staffing agencies (BEFORE Hunter to save credits) ───
    if exclude_staffing:
        try:
            hunter_cfg = load_hunter_config()
            brj_cfg = hunter_cfg.get("brj_specific", {})
            kw_list = brj_cfg.get("exclude_staffing_keywords", [])
            name_list = brj_cfg.get("exclude_staffing_companies", [])
            before = len(df_display)
            df_display, excluded_count, sample_names = filter_out_staffing_companies(df_display, kw_list, name_list)
            if excluded_count > 0:
                with st.expander(f"🚫 Excluded {excluded_count} staffing agencies (no Hunter credits spent)"):
                    st.caption("Filtered companies:")
                    for name in sample_names:
                        st.write(f"  • {name}")
                    if excluded_count > len(sample_names):
                        st.write(f"  ... and {excluded_count - len(sample_names)} more")
            st.caption(f"Staffing exclusion: {before} → {len(df_display)} relevant companies")
        except Exception as e:
            st.warning(f"Staffing filter failed (non-fatal): {e}")

    if df_display.empty:
        st.warning("No relevant companies after filters. Try broader keywords or uncheck 'Exclude staffing'.")
        st.stop()

    # ─── Domain enrichment ─────────────────────────────────────
    # Pipeline: company_url_direct → company_url → Indeed profile scrape → Google CSE → emails fallback
    try:
        hunter_cfg = load_hunter_config()
    except Exception:
        hunter_cfg = {}

    google_cse_configured = (
        hunter_cfg.get("google_cse", {}).get("cse_id", "").strip()
        and not hunter_cfg.get("google_cse", {}).get("cse_id", "").startswith("PASTE")
    )

    with st.status(f"Resolving real domains for {len(df_display)} companies...", expanded=False) as ds:
        progress_ds = st.progress(0, text="Starting...")

        def domain_progress(i, total, company, domain, source):
            label = f"{i}/{total} • {str(company)[:35]}"
            if domain:
                label += f" → {domain} ({source})"
            else:
                label += " (no domain found)"
            progress_ds.progress(i / total, text=label[:100])

        df_display = enrich_domains_in_dataframe(
            df_display, hunter_cfg,
            use_indeed_scrape=True,
            use_google_search=google_cse_configured,
            progress_cb=domain_progress,
        )
        progress_ds.empty()

        # Stats
        sources_breakdown = df_display["domain_source"].fillna("").value_counts().to_dict()
        domains_found = df_display["company_domain"].notna().sum()
        ds.update(
            label=f"✓ Domains resolved: {domains_found}/{len(df_display)}",
            state="complete",
        )

    # Show breakdown of sources
    if domains_found > 0:
        cols = st.columns(5)
        cols[0].metric("Total", len(df_display))
        cols[1].metric("Direct (JobSpy)", sources_breakdown.get("direct", 0) + sources_breakdown.get("company_url", 0))
        cols[2].metric("Indeed scrape", sources_breakdown.get("indeed_scrape", 0))
        cols[3].metric("Google CSE", sources_breakdown.get("google", 0))
        cols[4].metric("No domain", sources_breakdown.get("", 0) + len([s for s in df_display["domain_source"] if not s]))

    if not google_cse_configured:
        st.info("💡 Tip: configuring Google CSE in config.json boosts domain coverage 30→70%. Free 100 queries/day.")

    # ─── Hunter enrichment ─────────────────────────────────────
    if enrich_with_hunter:
        st.divider()
        st.subheader("🎯 Hunter Enrichment — searching for recruiters")

        # Solo dominios únicos
        domains_with_url = df_display["company_domain"].dropna().nunique() if "company_domain" in df_display.columns else 0
        st.caption(f"Companies with detectable URL: {domains_with_url}")

        progress = st.progress(0, text="Starting...")
        live_table = st.empty()
        rows_so_far = []

        def progress_cb(i, total, domain, result):
            label = domain or "(no domain)"
            if result.get("from_cache"):
                label += " [cache]"
            elif result.get("email"):
                label += f" → {result.get('first_name','')} {result.get('last_name','')} ({(result.get('position') or '')[:30]})"
            elif result.get("error"):
                label += f" [error: {result['error'][:40]}]"
            elif not result.get("first_name") and not result.get("error"):
                label += " [no data]"
            progress.progress(i / total, text=f"{i}/{total} • {label[:80]}")

        try:
            df_display = hunter_enrich(df_display, progress_cb=progress_cb)
            progress.empty()

            # Stats
            enriched = sum(1 for x in df_display.get("recruiter_email", []) if x)
            priority = sum(1 for x in df_display.get("recruiter_is_priority", []) if x)
            st.success(f"✓ Hunter enrichment complete: {enriched}/{len(df_display)} with contact, {priority} with priority role (recruiter/HR)")
        except Exception as e:
            progress.empty()
            st.error(f"Hunter enrichment error: {e}")
            st.exception(e)

    # ─── Display table ──────────────────────────────────────────
    st.divider()
    st.subheader(f"📋 Results ({len(df_display)} {'companies' if dedup_companies else 'vacancies'})")

    # Columns to show
    display_cols = ["company", "title", "location", "date_posted", "site"]
    if dedup_companies:
        display_cols.insert(2, "vacancy_count")
        display_cols.insert(3, "all_titles")

    if enrich_with_hunter:
        display_cols.extend([
            "recruiter_first_name", "recruiter_last_name",
            "recruiter_position", "recruiter_email", "recruiter_is_priority",
        ])

    display_cols.extend(["job_url", "company_url", "emails"])
    available_cols = [c for c in display_cols if c in df_display.columns]
    table_df = df_display[available_cols].copy()

    if "all_titles" in table_df.columns:
        table_df["all_titles"] = table_df["all_titles"].fillna("").str[:120]

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "job_url": st.column_config.LinkColumn("Job posting"),
            "company_url": st.column_config.LinkColumn("Company site"),
            "company": st.column_config.TextColumn("Company", width="medium"),
            "title": st.column_config.TextColumn("Job Title", width="medium"),
            "emails": st.column_config.TextColumn("Email(s) extracted", help="JobSpy extracts emails from job descriptions"),
        },
    )

    # ─── Download CSV ──────────────────────────────────────────
    csv_data = df_display.to_csv(index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kw = "".join(c if c.isalnum() else "_" for c in keywords[:30])
    st.download_button(
        "⬇ Download CSV (all columns)",
        data=csv_data,
        file_name=f"scm_jobs_{safe_kw}_{ts}.csv",
        mime="text/csv",
    )

    # Save run to history (tenant-scoped)
    from lib.paths import get_tenant_searches_dir
    history_dir = get_tenant_searches_dir(user["tenant"])
    df_display.to_csv(history_dir / f"search_{ts}_{safe_kw}.csv", index=False)

    # ─── Persist in session_state to survive reruns ──────────
    st.session_state["jobs_results"] = df_display
    st.session_state["jobs_results_meta"] = {
        "keywords": keywords,
        "dedup": dedup_companies,
        "filename": f"scm_jobs_{safe_kw}_{ts}.csv",
        "timestamp": ts,
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    st.success(f"✓ Run saved to tenant history ({user['tenant']}) — search_{ts}_{safe_kw}.csv")

    # ─── Stats ────────────────────────────────────────────────
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total vacancies", len(df))
    c2.metric("Unique companies", df["company"].nunique() if "company" in df.columns else 0)

    with_email = df["emails"].notna().sum() if "emails" in df.columns else 0
    c3.metric("With extracted email", with_email)

    with_url = df["company_url"].notna().sum() if "company_url" in df.columns else 0
    c4.metric("With company URL", with_url)
