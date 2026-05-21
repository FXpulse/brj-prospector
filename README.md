# 🎯 BRJ Prospector

Herramienta de prospecting para **Bilingual Recruiters Jacksonville** (BRJ). Automatiza la búsqueda de:

- **Pipeline A — Job vacancies**: encuentra vacantes en múltiples job boards (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google for Jobs), identifica la empresa que postea, y enriquece con el contacto del recruiter via Hunter.io.

- **Pipeline B — Companies que usan staffing**: detecta empresas con alta necesidad de staffing externo basado en volumen de vacantes + industria. Por cada empresa con signal, encuentra al decision-maker (HR Director, Plant Manager, Operations) via Hunter.io.

Built with Python + Streamlit. Zero-cost stack: JobSpy (free), Hunter.io free/paid tier, Google Custom Search API (free 100/day).

## Setup local

### Requisitos

- Python 3.10+
- API key de Hunter.io (free tier = 25 lookups/mes; paid tiers desde $49/mo para 500+)
- API key de Google Cloud con Custom Search API enabled
- PIT (Private Integration Token) de GoHighLevel

### Instalación

```bash
# Clonar
git clone https://github.com/YOUR_USERNAME/brj-prospector.git
cd brj-prospector

# Crear virtual env (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencies
pip install -r requirements.txt

# Configurar credenciales
cp config.template.json config.json
# Editar config.json y reemplazar PASTE_* con tus keys reales
```

### Configuración de config.json

Editar `config.json` con tus credenciales:

```json
{
  "ghl": {
    "location_id": "tu_location_id_ghl",
    "pit": "pit-xxxx-xxxx-xxxx",
    "base_url": "https://services.leadconnectorhq.com",
    "api_version": "2021-07-28"
  },
  "hunter": {
    "api_key": "tu_hunter_api_key",
    "monthly_limit": 1000
  },
  "google_cse": {
    "api_key": "tu_google_api_key",
    "cse_id": "tu_cse_id"
  }
}
```

**⚠️ `config.json` está en `.gitignore` y NO se commitea**. Tus keys quedan solo en tu máquina.

### Levantar la app

```bash
python -m streamlit run app.py
```

Browser se abre solo en `http://localhost:8501`.

Para correr en otro puerto:
```bash
python -m streamlit run app.py --server.port 8502
```

## Estructura del proyecto

```
brj-prospector/
├── app.py                       # Streamlit main entry
├── pages/
│   ├── 1_Job_Search.py          # Pipeline A — vacantes + recruiter lookup
│   └── 2_Companies.py           # Pipeline B — empresas que usan staffing
├── lib/
│   ├── jobspy_search.py         # Wrapper JobSpy + filters + dedup
│   ├── hunter_enrich.py         # Hunter.io con role priority (A: recruiter, B: HR decision-maker)
│   ├── domain_lookup.py         # Resuelve domain real via JobSpy + Indeed scrape + Google CSE
│   ├── industry_keywords.py     # Keywords pre-armados por industria (Manufacturing, Hospitality, etc.)
│   └── company_state.py         # Tracking persistente de empresas vistas/contactadas
├── data/                        # State files locales (gitignored)
│   ├── company_state.json       # Empresas tracked + status (NEW / IN_DB / CONTACTED)
│   ├── hunter_cache.json        # Cache de lookups Hunter por domain
│   ├── hunter_credits.json      # Tracking de credits Hunter usados
│   ├── domain_cache.json        # Cache de domain resolutions
│   └── searches/                # CSVs históricos de cada run
├── tests/                       # Scripts de test/debug (no son production)
├── requirements.txt
├── config.template.json         # Template (sin secrets)
├── config.json                  # Tus credenciales reales (gitignored)
└── README.md
```

## Pipelines

### Pipeline A — Job Search

**Use case**: encontrar vacantes abiertas en industrias específicas + identificar al recruiter de cada empresa que postea.

**Output**: tabla con company, job title, location, date, recruiter contact (cuando Hunter lo encuentra).

**Costo por run**: Hunter usa 1 credit por empresa única (cached). Google Places no se usa (es JobSpy).

### Pipeline B — Companies

**Use case**: detectar empresas con 5+ vacantes abiertas en una industria (signal de staffing externo) + encontrar HR/Operations decision-maker.

**Output**: ranked list de "high-staffing-need" companies + decision-maker contact.

**Industrias soportadas**:
- Manufacturing (más detallado — 20 keywords)
- Hospitality
- Logistics & Warehouse
- Healthcare
- Construction
- Restaurants & Food Service
- Retail

**Costo por run**: Hunter usa 1 credit por empresa única (cached). Google Custom Search usa 1 query por company sin domain detectado por JobSpy.

## Sources soportadas

| Source | Estado | Notas |
|---|---|---|
| Indeed | ✅ | Funciona bien. Limitado al rate de JobSpy. |
| LinkedIn Jobs | ✅ | Funciona, slow. |
| Glassdoor | ⚠️ | A veces falla "location not parsed". Usar formato exacto. |
| ZipRecruiter | ❌ | Cloudflare bloquea scraping. Sin proxies pagos. |
| Google for Jobs | ✅ | Funciona como meta-aggregator. |

## Deploy a Streamlit Cloud (opcional)

1. Push repo a GitHub (asumimos repo privado por las API keys aunque estén gitignored)
2. https://share.streamlit.io → New app → conectar repo
3. App settings → **Secrets** → pegar el contenido de `config.json` en formato TOML:

```toml
[ghl]
location_id = "..."
pit = "pit-..."
base_url = "https://services.leadconnectorhq.com"
api_version = "2021-07-28"

[hunter]
api_key = "..."
monthly_limit = 1000

[google_cse]
api_key = "..."
cse_id = "..."

[brj_specific]
recruiter_role_keywords = ["recruiter", "...", "..."]
# ... (etc)
```

4. Deploy. URL pública del app aparece en ~2 min.

**Nota**: el código actual lee config desde `config.json`. Para usar `st.secrets` en producción cloud, hay que refactorizar el loader. Ver issue futuro.

## Workflow recomendado para BRJ recruiters

### Sesión semanal de prospecting (~30-45 min)

```
1. Pipeline B → Manufacturing en Jacksonville, FL (5+ vacantes)
   → Lista de 15-25 empresas con signal alto
2. Filter sidebar: ☑ Ocultar contactadas (default)
3. Para cada empresa:
   - Click LinkedIn link del decision-maker
   - Mandar DM personalizado
4. Click "Marcar las N como contactadas" al final
5. Repeat semana siguiente — sistema oculta auto las contactadas
```

## Limitaciones conocidas

- **ZipRecruiter blocked**: Cloudflare anti-bot. Sin proxies, no funciona.
- **Indeed company profile scrape blocked**: Security check. Por eso usamos Google CSE como fallback.
- **Google CSE 100 queries/day free**: Si excedés, no impacta el resto del tool — solo bajaría coverage de domains.
- **Hunter credits caducables**: Free tier reset mensual. Si BRJ usa pesado, considerar upgrade a paid tier.
- **JobSpy + LinkedIn intermitente**: LinkedIn cambia su HTML seguido. Si falla, esperar update de JobSpy (mantenimiento de la comunidad).

## Roadmap (no implementado todavía)

- [ ] Multi-user auth con login por usuario
- [ ] History page con todas las búsquedas pasadas
- [ ] Saved presets de búsqueda (1-click re-run)
- [ ] GHL push de prospects con tags dinámicas
- [ ] Email outreach automation desde el app (templates + send via Hunter campaigns)
- [ ] Refactor para usar Streamlit secrets en cloud deploy
- [ ] Pipeline C — companies por intent signals (press releases, hiring announcements)

## License

Internal use only — BRJ + family. No license public.
