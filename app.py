"""
app.py - BRJ Prospector main entry.

Run: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="BRJ Prospector",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 BRJ Prospector")
st.markdown(
    """
Herramienta de prospecting para **Bilingual Recruiters Jacksonville** — automatiza la búsqueda
de vacantes en múltiples job boards y enriquece con datos de la empresa solicitante.

Usá el menú lateral para navegar:

- 🔍 **Job Search** — buscar vacantes en Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google
- 🏢 **Companies** — base de datos de empresas (próximamente)
- 📊 **History** — búsquedas anteriores
- ⚙️ **Settings** — config + admin
"""
)

st.divider()

# Quick stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Job Boards activos", "5", help="Indeed + LinkedIn + Glassdoor + ZipRecruiter + Google for Jobs")
with col2:
    st.metric("Búsquedas guardadas", "0", help="Vas a poder guardar presets")
with col3:
    st.metric("Hunter credits remaining", "—", help="Se carga en cada run")

st.info("👉 Arrancá por **Job Search** en el menú lateral.")
