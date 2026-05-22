"""
3_History.py - Historial de todas las búsquedas pasadas.

Lee data/clients/<tenant>/searches/*.csv (Pipeline A + B exports) y muestra:
- Lista paginada de runs (orden desc por fecha)
- Por cada run: timestamp, tipo (Job Search / Companies), label, # filas
- Preview expandible + download CSV
"""
import sys
import re
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCRIPT_DIR = Path(__file__).resolve().parent.parent

st.set_page_config(page_title="History - SCM Prospector", page_icon="📊", layout="wide")
from lib.styling import apply_brand_styles, brand_header
from lib.auth import require_auth, render_user_chip
from lib.paths import get_tenant_searches_dir
apply_brand_styles()
user = require_auth()
render_user_chip(user)
brand_header(
    "📊 History",
    f"Saved searches for {user['tenant'].upper()} — Pipeline A (Job Search) + Pipeline B (Companies)",
)

SEARCHES_DIR = get_tenant_searches_dir(user["tenant"])


def parse_filename(filename):
    """Extrae metadata del nombre del archivo CSV.

    Formats esperados:
      search_YYYYMMDD_HHMMSS_TAG.csv  → Pipeline A
      companies_YYYYMMDD_HHMMSS_INDUSTRY.csv → Pipeline B
    """
    stem = Path(filename).stem
    if stem.startswith("companies_"):
        pipeline = "🏢 Companies"
        rest = stem[len("companies_"):]
    elif stem.startswith("search_"):
        pipeline = "🔍 Job Search"
        rest = stem[len("search_"):]
    else:
        pipeline = "📄 Other"
        rest = stem

    match = re.match(r"(\d{8})_(\d{6})_(.+)", rest)
    if match:
        date_str, time_str, label = match.groups()
        try:
            ts = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        except Exception:
            ts = None
    else:
        ts = None
        label = rest

    return {
        "pipeline": pipeline,
        "timestamp": ts,
        "label": label.replace("_", " "),
    }


# ─── Load all search files ─────────────────────────────────────
if not SEARCHES_DIR.exists():
    st.warning("No searches folder yet for this tenant. Run a search in Job Search or Companies first.")
    st.stop()

csv_files = list(SEARCHES_DIR.glob("*.csv"))
if not csv_files:
    st.info("No saved searches yet. Run something in Job Search or Companies to start building history.")
    st.stop()

records = []
for f in csv_files:
    meta = parse_filename(f.name)
    try:
        size_kb = f.stat().st_size / 1024
        with open(f, "r", encoding="utf-8") as fh:
            n_rows = sum(1 for _ in fh) - 1  # minus header
    except Exception:
        size_kb = 0
        n_rows = 0

    records.append({
        "timestamp": meta["timestamp"] or datetime.fromtimestamp(f.stat().st_mtime),
        "pipeline": meta["pipeline"],
        "label": meta["label"],
        "rows": n_rows,
        "size_kb": round(size_kb, 1),
        "filename": f.name,
        "path": str(f),
    })

records.sort(key=lambda r: r["timestamp"], reverse=True)
df_history = pd.DataFrame(records)

# ─── Sidebar filters ───────────────────────────────────────────
with st.sidebar:
    st.header("🔎 Filters")

    pipelines = sorted(df_history["pipeline"].unique())
    selected_pipelines = st.multiselect(
        "Pipeline",
        options=pipelines,
        default=pipelines,
    )

    if len(df_history) > 0:
        min_date = df_history["timestamp"].min()
        max_date = df_history["timestamp"].max()
        st.caption(f"Available range: {min_date.strftime('%Y-%m-%d')} → {max_date.strftime('%Y-%m-%d')}")

    label_search = st.text_input("Search by label", placeholder="ex: Staffing, warehouse...")

# ─── Apply filters ─────────────────────────────────────────────
filtered = df_history.copy()
if selected_pipelines:
    filtered = filtered[filtered["pipeline"].isin(selected_pipelines)]
if label_search:
    filtered = filtered[filtered["label"].str.contains(label_search, case=False, na=False)]

# ─── Top stats ──────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total runs", len(df_history))
col2.metric("Filtered", len(filtered))
col3.metric("Job Search runs", (df_history["pipeline"] == "🔍 Job Search").sum())
col4.metric("Companies runs", (df_history["pipeline"] == "🏢 Companies").sum())

# ─── Paginated list ────────────────────────────────────────────
st.divider()

if filtered.empty:
    st.info("No runs match the filters.")
    st.stop()

st.subheader(f"Runs ({len(filtered)})")

display_df = filtered[["timestamp", "pipeline", "label", "rows", "size_kb"]].copy()
display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
display_df.columns = ["Date", "Pipeline", "Label", "Rows", "Size KB"]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rows": st.column_config.NumberColumn("Rows", help="Number of results in this run"),
        "Size KB": st.column_config.NumberColumn("Size KB", help="CSV file size"),
    },
)

# ─── Detail viewer ─────────────────────────────────────────────
st.divider()
st.subheader("📂 View run details")

run_options = [
    f"{r['timestamp'].strftime('%Y-%m-%d %H:%M')} • {r['pipeline']} • {r['label']} ({r['rows']} rows)"
    for _, r in filtered.iterrows()
]
selected_run = st.selectbox("Select a run", options=run_options, index=0 if run_options else None)

if selected_run:
    idx = run_options.index(selected_run)
    record = filtered.iloc[idx]
    file_path = Path(record["path"])

    try:
        run_df = pd.read_csv(file_path)
        st.caption(f"File: {record['filename']} • {len(run_df)} rows • {len(run_df.columns)} columns")

        st.dataframe(run_df.head(50), use_container_width=True, hide_index=True)

        if len(run_df) > 50:
            st.caption(f"Preview shows first 50 rows of {len(run_df)}. Download the CSV to see all.")

        csv_bytes = run_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"⬇ Download {record['filename']}",
            data=csv_bytes,
            file_name=record['filename'],
            mime="text/csv",
        )
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
