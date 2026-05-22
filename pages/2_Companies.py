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

st.set_page_config(page_title="Companies (Pipeline B) - BRJ Prospector", page_icon="🏢", layout="wide")
from lib.styling import apply_brand_styles, brand_header
apply_brand_styles()
brand_header(
    "🏢 Companies — Empresas que usan staffing",
    "Detecta empresas con ALTA necesidad de staffing externo basado en volumen + tipo de vacantes",
)

# ─── Sidebar: stats globales del state ──────────────────────────
with st.sidebar:
    st.header("📊 Database global")
    cs = load_company_state()
    stats = get_company_stats(cs)
    st.metric("Total empresas tracked", stats["total_companies"])
    col_a, col_b = st.columns(2)
    col_a.metric("Contactadas", stats["contacted"])
    col_b.metric("En DB (pendientes)", stats["in_db_not_contacted"])
    st.caption(f"🌐 {stats['with_domain']} con domain · 🎯 {stats['with_decision_maker']} con DM contact")

    st.divider()
    st.subheader("🔎 Filtros de display")
    hide_contacted = st.checkbox("Ocultar contactadas (default)", value=True,
                                 help="Esconde empresas ya marcadas como contactadas. Recomendado para no saturar prospects.")
    only_new = st.checkbox("Mostrar solo NEW", value=False,
                          help="Esconde empresas que ya están en la DB. Útil para descubrir solo prospects nuevos.")

# ─── Industry selector + info ───────────────────────────────────
industries = get_industries()

col_ind, col_thresh, col_lookback = st.columns([2, 1, 1])
with col_ind:
    industry = st.selectbox(
        "Industria",
        options=industries,
        index=industries.index("Manufacturing") if "Manufacturing" in industries else 0,
        help="Cada industria tiene 10-15 keywords pre-armadas. Manufacturing es el más profundo (core BRJ).",
    )
    industry_cfg = get_industry_config(industry)
    st.caption(f"📍 {industry_cfg.get('description', '')}")
    st.caption(f"🌎 NE Florida density: {industry_cfg.get('ne_florida_density', '')}")

with col_thresh:
    min_vacancies = st.number_input(
        "Min vacantes",
        min_value=2,
        max_value=50,
        value=5,
        help="Empresas con >= N vacantes abiertas en el período. 5+ = signal fuerte de staffing externo.",
    )

with col_lookback:
    lookback = st.selectbox(
        "Lookback",
        options=["7d", "14d", "30d"],
        index=1,
        help="Período de búsqueda. 14d es sweet spot.",
    )

# ─── Locations ──────────────────────────────────────────────────
st.markdown("**Locations** (una por línea)")
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
with st.expander(f"📋 Ver las {len(queries)} queries que se van a correr para {industry}"):
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
        help="Busca HR Director / Plant Manager / Operations al final, solo en empresas con >= min_vacancies. Cache evita re-queries.",
    )
with col_max:
    max_per_query = st.number_input("Max per query", min_value=10, max_value=100, value=30, step=10)
with col_run:
    st.markdown("&nbsp;")
    run = st.button("🚀 Find Companies", type="primary", use_container_width=True)

# ─── Restore previous results from session if available ────────
# Esto evita perder data si el user hace cualquier rerun (click, refresh)
if "companies_results" in st.session_state and not run:
    st.info(
        "💾 Resultados del último run cargados desde session. "
        "Click 🚀 Find Companies para correr de nuevo."
    )
    grouped_cached = st.session_state["companies_results"]
    last_run_info = st.session_state.get("companies_results_meta", {})

    st.divider()
    st.subheader(f"📋 {len(grouped_cached)} empresas — {last_run_info.get('industry', '?')} (cached)")
    st.dataframe(grouped_cached, use_container_width=True, hide_index=True)

    csv_data_cached = grouped_cached.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Re-download CSV del último run",
        data=csv_data_cached,
        file_name=last_run_info.get("filename", "results.csv"),
        mime="text/csv",
    )

# ─── Run logic ──────────────────────────────────────────────────
if run:
    if not sources:
        st.error("Seleccioná al menos 1 source.")
        st.stop()
    if not queries:
        st.error(f"No hay queries definidas para {industry}.")
        st.stop()
    if not locations:
        st.error("Agregá al menos 1 location.")
        st.stop()

    st.divider()

    # Step 1: run all queries × all locations
    total_runs = len(queries) * len(locations) * len(sources)
    st.info(f"⏱ Estimado: {len(queries)} queries × {len(locations)} locations × {len(sources)} sources = {total_runs} micro-searches. Toma 2-5 minutos.")

    all_jobs = []
    prog = st.progress(0, text=f"Iniciando — 0 / {len(queries)} queries")

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
            st.warning(f"Query '{query[:40]}' falló: {e}")
        time.sleep(0.5)

    prog.empty()

    if not all_jobs:
        st.warning("Sin resultados de ninguna query. Probá otra industria o ampliá lookback.")
        st.stop()

    df_all = pd.concat(all_jobs, ignore_index=True)
    st.success(f"✓ {len(df_all)} vacantes raw scrapeadas across {len(queries)} queries")

    # Step 2: aggregate by company
    st.divider()
    st.subheader("📊 Aggregating por empresa...")

    # Clean company name + agrupar
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

    # Rename for downstream compatibility
    grouped = grouped.rename(columns={
        "first_company_name": "company",
        "first_company_url": "company_url",
        "first_company_url_direct": "company_url_direct",
        "first_emails": "emails",
        "first_location": "location",
        "first_date": "date_posted",
    })

    # Filter por threshold
    before_thresh = len(grouped)
    grouped = grouped[grouped["vacancy_count"] >= min_vacancies].copy()
    st.caption(f"Threshold filter ({min_vacancies}+ vacantes): {before_thresh} empresas → {len(grouped)} con signal")

    if grouped.empty:
        st.warning(f"Ninguna empresa con {min_vacancies}+ vacantes. Probá threshold menor o ampliá lookback.")
        st.stop()

    # Sort by vacancy count desc
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
            with st.expander(f"🚫 Excluidas {excluded_count} companies (staffing agencies + chains gigantes)"):
                for s in sample:
                    st.write(f"  • {s}")
        st.caption(f"Filtro staffing+chains: {before_filter} → {len(grouped)} prospects relevantes")
    except Exception as e:
        st.warning(f"Filter failed (no fatal): {e}")
        cfg = {}

    if grouped.empty:
        st.warning("Nada quedó después de filters. Revisá thresholds.")
        st.stop()

    # Step 4: domain enrichment
    st.divider()
    st.subheader("🌐 Resolviendo dominios reales...")

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
        use_google_search=google_cse_ok,  # solo si está configurado
        progress_cb=dcb,
    )
    dprogress.empty()

    domains_found = grouped["company_domain"].notna().sum()
    st.success(f"✓ Dominios: {domains_found}/{len(grouped)} resueltos")

    # Step 4b: Company phones via Google Places
    st.divider()
    st.subheader("📞 Resolviendo phones de cada empresa...")

    pprogress = st.progress(0, text="Iniciando...")
    def pcb(i, total, company, phone):
        label = f"{i}/{total} • {str(company)[:35]}"
        if phone:
            label += f" → {phone}"
        pprogress.progress(i / total, text=label[:90])

    grouped = enrich_phones_in_dataframe(grouped, cfg, progress_cb=pcb)
    pprogress.empty()

    phones_found = sum(1 for p in grouped.get("company_phone", []) if p)
    st.success(f"✓ Phones: {phones_found}/{len(grouped)} encontrados via Google Places")

    # Step 5: Hunter HR enrichment
    if enrich_hunter and domains_found > 0:
        st.divider()
        st.subheader("🎯 Hunter — buscando HR decision-makers")

        priority_roles = get_decision_maker_roles(industry)
        st.caption(f"Priorizando roles para {industry}: {', '.join(priority_roles[:5])}…")

        credits_state = load_credits_state()
        hunter_cache = _hunter_load_cache(HUNTER_CACHE_FILE, {})

        hprogress = st.progress(0, text="...")
        decision_makers = []

        for i, row in enumerate(grouped.itertuples(index=False)):
            domain = getattr(row, "company_domain", None)
            company = getattr(row, "company", "?")

            if not domain:
                decision_makers.append({})
                hprogress.progress((i + 1) / len(grouped), text=f"{i+1}/{len(grouped)} • {company[:30]} • (no domain)")
                continue

            # Check cache by domain+pipeline
            cache_key = f"{domain}__pipelineB"
            if cache_key in hunter_cache:
                result = {**hunter_cache[cache_key], "from_cache": True}
            else:
                if credits_state.get("used", 0) >= cfg.get("hunter", {}).get("monthly_limit", 1000):
                    decision_makers.append({"error": "credits exhausted"})
                    continue
                result = find_decision_maker_at_domain(domain, cfg, priority_roles=priority_roles)
                if not result.get("error"):
                    credits_state["used"] = credits_state.get("used", 0) + 1
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

        # Add Hunter results as columns
        grouped["dm_first_name"] = [d.get("first_name", "") for d in decision_makers]
        grouped["dm_last_name"] = [d.get("last_name", "") for d in decision_makers]
        grouped["dm_position"] = [d.get("position", "") for d in decision_makers]
        grouped["dm_email"] = [d.get("email", "") for d in decision_makers]
        grouped["dm_phone"] = [d.get("phone", "") for d in decision_makers]  # NUEVO
        grouped["dm_is_priority_role"] = [d.get("is_priority_role", False) for d in decision_makers]
        grouped["dm_confidence"] = [d.get("confidence", "") for d in decision_makers]

        hprogress.empty()
        with_dm = sum(1 for d in decision_makers if d.get("email"))
        priority_dm = sum(1 for d in decision_makers if d.get("is_priority_role"))
        st.success(f"✓ Hunter: {with_dm}/{len(grouped)} con decision-maker, {priority_dm} en role priority (HR/Ops/GM)")

    # ─── State sync — clasificar empresas: NEW / IN_DB / CONTACTED ───
    company_state = load_company_state()
    statuses = []
    for _, row in grouped.iterrows():
        st_info = get_company_status(company_state, row.get("company", ""), row.get("location", ""))
        statuses.append(st_info["status"])
    grouped["status"] = statuses

    # Upsert TODOS al state (registra appearance) — domain + DM si lo trajimos
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

    # ─── Apply user filters (hide contacted / only new) ──────────
    before_filter = len(grouped)
    if hide_contacted:
        grouped = grouped[grouped["status"] != "CONTACTED"]
    if only_new:
        grouped = grouped[grouped["status"] == "NEW"]

    filter_caption = f"Filtros UI: {before_filter} → {len(grouped)}"
    if hide_contacted:
        filter_caption += f" (ocultas {sum(1 for s in statuses if s == 'CONTACTED')} ya contactadas)"
    if only_new:
        filter_caption += f" (solo NEW)"
    st.caption(filter_caption)

    if grouped.empty:
        st.info("No hay empresas que mostrar con los filtros actuales. Desmarcá filtros o cambiá la búsqueda.")
        st.stop()

    # ─── Final table ────────────────────────────────────────────
    st.divider()
    st.subheader(f"📋 {len(grouped)} empresas con signal de staffing — {industry}")

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
            "status": st.column_config.TextColumn("Status", help="NEW=primera vez. IN_DB=ya tracked. CONTACTED=ya contactada (filtrada por default)."),
            "vacancy_count": st.column_config.NumberColumn("Vacantes", help="Total vacantes en el período"),
            "company_phone": st.column_config.TextColumn("📞 Company phone", help="Teléfono general de la empresa via Google Places"),
            "sample_titles": st.column_config.TextColumn("Sample títulos"),
            "queries_matched": st.column_config.TextColumn("Queries match"),
            "dm_first_name": st.column_config.TextColumn("Decision-maker name"),
            "dm_position": st.column_config.TextColumn("Position"),
            "dm_email": st.column_config.TextColumn("Email"),
            "dm_phone": st.column_config.TextColumn("📱 DM direct phone", help="Phone directo del decision-maker (raro — Hunter solo lo trae a veces)"),
            "dm_is_priority_role": st.column_config.CheckboxColumn("Priority role"),
            "company_url": st.column_config.LinkColumn("Indeed/JB"),
        },
    )

    # ─── Bulk action: marcar como contactadas ────────────────────
    st.divider()
    st.subheader("📌 Acciones bulk")

    col_action, col_note = st.columns([1, 2])
    with col_action:
        if st.button(f"✓ Marcar las {len(grouped)} como contactadas", use_container_width=True):
            items = [(row["company"], row.get("location", "")) for _, row in grouped.iterrows()]
            company_state = load_company_state()
            company_state = mark_many_as_contacted(company_state, items, note=f"Marcadas bulk desde {industry} run {datetime.now().strftime('%Y-%m-%d')}")
            save_company_state(company_state)
            st.success(f"✓ {len(items)} empresas marcadas como contactadas. Próximas búsquedas las van a ocultar.")
            st.caption("Refrescá la página para ver el filter aplicado.")
    with col_note:
        st.caption(
            "💡 **Workflow recomendado**: después de hacer outreach manual a las empresas de esta lista "
            "(LinkedIn DMs, emails, calls), cliqueá este botón. Las próximas búsquedas las van a saltear "
            "automáticamente. Si necesitás verlas de nuevo, desmarcá 'Ocultar contactadas' en el sidebar."
        )

    # Stats
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Empresas (prospects)", len(grouped))
    c2.metric("Vacantes totales", int(grouped["vacancy_count"].sum()))
    if enrich_hunter:
        with_dm = sum(1 for x in grouped.get("dm_email", []) if x)
        c3.metric("Con HR contact", with_dm)
        prio = sum(1 for x in grouped.get("dm_is_priority_role", []) if x)
        c4.metric("Priority role", prio)

    # Download
    csv_data = grouped.to_csv(index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "⬇ Download CSV (todas las columnas)",
        data=csv_data,
        file_name=f"brj_companies_{industry.replace(' ', '_')}_{ts}.csv",
        mime="text/csv",
    )

    # Save to history
    history_dir = Path(__file__).resolve().parent.parent / "data" / "searches"
    history_dir.mkdir(parents=True, exist_ok=True)
    csv_filename = f"companies_{ts}_{industry.replace(' ', '_')}.csv"
    grouped.to_csv(history_dir / csv_filename, index=False)
    st.caption(f"✓ Run guardado en data/searches/{csv_filename}")

    # ─── Persistir en session_state para survive reruns ──────────
    st.session_state["companies_results"] = grouped
    st.session_state["companies_results_meta"] = {
        "industry": industry,
        "filename": f"brj_companies_{industry.replace(' ', '_')}_{ts}.csv",
        "timestamp": ts,
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
