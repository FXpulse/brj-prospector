"""
3_History.py - Historial de todas las búsquedas pasadas.

Lee data/searches/*.csv (Pipeline A + B exports) y muestra:
- Lista paginada de runs (orden desc por fecha)
- Por cada run: timestamp, tipo (Job Search / Companies), label, # filas
- Preview expandible + download CSV

Nota: en Streamlit Cloud deploy, data/ NO persiste entre restarts del container.
Para historial persistente cloud-side, hay que migrar a DB externa (futuro).
"""
import sys
import re
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCRIPT_DIR = Path(__file__).resolve().parent.parent
SEARCHES_DIR = SCRIPT_DIR / "data" / "searches"

st.set_page_config(page_title="History - BRJ Prospector", page_icon="📊", layout="wide")
st.title("📊 History")
st.caption("Todas las búsquedas guardadas — Pipeline A (Job Search) + Pipeline B (Companies)")


def parse_filename(filename):
    """Extrae metadata del nombre del archivo CSV.

    Formats esperados:
      search_YYYYMMDD_HHMMSS_TAG.csv  → Pipeline A
      companies_YYYYMMDD_HHMMSS_INDUSTRY.csv → Pipeline B
    """
    stem = Path(filename).stem
    # Detect pipeline type
    if stem.startswith("companies_"):
        pipeline = "🏢 Companies"
        rest = stem[len("companies_"):]
    elif stem.startswith("search_"):
        pipeline = "🔍 Job Search"
        rest = stem[len("search_"):]
    else:
        pipeline = "📄 Other"
        rest = stem

    # Try to extract timestamp YYYYMMDD_HHMMSS
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
    st.warning("Carpeta data/searches/ no existe todavía. Corré una búsqueda en Job Search o Companies primero.")
    st.stop()

csv_files = list(SEARCHES_DIR.glob("*.csv"))
if not csv_files:
    st.info("Sin búsquedas guardadas todavía. Corré algo en Job Search o Companies para crear el primer historial.")
    st.stop()

# Build records
records = []
for f in csv_files:
    meta = parse_filename(f.name)
    try:
        size_kb = f.stat().st_size / 1024
        # Count rows (cheap — just count lines)
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

# Sort desc by timestamp
records.sort(key=lambda r: r["timestamp"], reverse=True)
df_history = pd.DataFrame(records)

# ─── Sidebar filters ───────────────────────────────────────────
with st.sidebar:
    st.header("🔎 Filtros")

    # Pipeline filter
    pipelines = sorted(df_history["pipeline"].unique())
    selected_pipelines = st.multiselect(
        "Pipeline",
        options=pipelines,
        default=pipelines,
    )

    # Date range
    if len(df_history) > 0:
        min_date = df_history["timestamp"].min()
        max_date = df_history["timestamp"].max()
        st.caption(f"Range disponible: {min_date.strftime('%Y-%m-%d')} → {max_date.strftime('%Y-%m-%d')}")

    # Search by label
    label_search = st.text_input("Buscar en label", placeholder="ej: Staffing, warehouse...")

# ─── Apply filters ─────────────────────────────────────────────
filtered = df_history.copy()
if selected_pipelines:
    filtered = filtered[filtered["pipeline"].isin(selected_pipelines)]
if label_search:
    filtered = filtered[filtered["label"].str.contains(label_search, case=False, na=False)]

# ─── Stats arriba ──────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total runs", len(df_history))
col2.metric("Filtered", len(filtered))
col3.metric("Job Search runs", (df_history["pipeline"] == "🔍 Job Search").sum())
col4.metric("Companies runs", (df_history["pipeline"] == "🏢 Companies").sum())

# ─── Lista paginada ────────────────────────────────────────────
st.divider()

if filtered.empty:
    st.info("Sin runs que coincidan con los filtros.")
    st.stop()

# Tabla principal
st.subheader(f"Runs ({len(filtered)})")

display_df = filtered[["timestamp", "pipeline", "label", "rows", "size_kb"]].copy()
display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
display_df.columns = ["Fecha", "Pipeline", "Label", "Filas", "Size KB"]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Filas": st.column_config.NumberColumn("Filas", help="Cantidad de resultados en este run"),
        "Size KB": st.column_config.NumberColumn("Size KB", help="Tamaño del CSV"),
    },
)

# ─── Detail viewer ─────────────────────────────────────────────
st.divider()
st.subheader("📂 Ver detalle de un run")

run_options = [
    f"{r['timestamp'].strftime('%Y-%m-%d %H:%M')} • {r['pipeline']} • {r['label']} ({r['rows']} filas)"
    for _, r in filtered.iterrows()
]
selected_run = st.selectbox("Seleccioná un run", options=run_options, index=0 if run_options else None)

if selected_run:
    # Find which record was selected
    idx = run_options.index(selected_run)
    record = filtered.iloc[idx]
    file_path = Path(record["path"])

    try:
        run_df = pd.read_csv(file_path)
        st.caption(f"Archivo: {record['filename']} • {len(run_df)} filas • {len(run_df.columns)} columnas")

        # Preview (first 50 rows)
        st.dataframe(run_df.head(50), use_container_width=True, hide_index=True)

        if len(run_df) > 50:
            st.caption(f"Preview muestra primeras 50 filas de {len(run_df)}. Descargá el CSV para ver todo.")

        # Download
        csv_bytes = run_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"⬇ Download {record['filename']}",
            data=csv_bytes,
            file_name=record['filename'],
            mime="text/csv",
        )
    except Exception as e:
        st.error(f"Error leyendo CSV: {e}")
