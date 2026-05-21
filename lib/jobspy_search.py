"""
jobspy_search.py - Wrapper sobre JobSpy con error handling + post-processing.

Funciones:
- run_search(): ejecuta scrape multi-source y devuelve DataFrame
- enrich_companies(): dedup por empresa + extrae emails embebidos
- filter_keywords(): filter adicional por keywords en title/description
"""
import time
from typing import List, Optional
from urllib.parse import urlparse

import pandas as pd
from jobspy import scrape_jobs


# Source name mapping (UI → JobSpy)
SOURCE_NAMES = {
    "indeed": "indeed",
    "linkedin": "linkedin",
    "zip_recruiter": "zip_recruiter",
    "glassdoor": "glassdoor",
    "google": "google",
}

# Posted date → hours_old
HOURS_LOOKUP = {
    "24h": 24,
    "48h": 48,
    "7d": 168,
    "14d": 336,
    "30d": 720,
}


def run_search(
    keywords: str,
    locations: List[str],
    sources: List[str],
    posted: str = "7d",
    results_per_query: int = 50,
    job_type: Optional[str] = None,
    country: str = "USA",
) -> pd.DataFrame:
    """
    Ejecuta búsqueda multi-source multi-location.

    Hace 1 search por (location × source). JobSpy permite multiples sources
    en una llamada — más eficiente — pero algunas locations específicas
    requieren queries separadas.

    Args:
        keywords: search term (ej. "warehouse worker")
        locations: lista de ubicaciones (ej. ["Jacksonville, FL", "32256"])
        sources: lista UI source names (ej. ["indeed", "linkedin"])
        posted: 24h/48h/7d/14d/30d
        results_per_query: max por cada (location × source)
        job_type: fulltime/parttime/contract/internship o None
        country: para Indeed/Glassdoor

    Returns:
        DataFrame con TODAS las jobs encontradas (de todas locations + sources)
    """
    if not locations:
        locations = [""]  # global search

    jobspy_sources = [SOURCE_NAMES[s] for s in sources if s in SOURCE_NAMES]
    if not jobspy_sources:
        raise ValueError(f"Ninguna source válida en {sources}. Disponibles: {list(SOURCE_NAMES.keys())}")

    hours_old = HOURS_LOOKUP.get(posted, 168)

    all_jobs = []
    errors = []

    for loc in locations:
        try:
            df = scrape_jobs(
                site_name=jobspy_sources,
                search_term=keywords,
                location=loc,
                results_wanted=results_per_query,
                hours_old=hours_old,
                country_indeed=country,
                job_type=job_type,
                linkedin_fetch_description=False,  # más rápido
                verbose=0,
            )
            if df is not None and len(df) > 0:
                df["search_location"] = loc  # tag para tracking
                all_jobs.append(df)
        except Exception as e:
            errors.append({"location": loc, "error": str(e)})

        time.sleep(1)  # polite delay entre queries

    if not all_jobs:
        return pd.DataFrame(), errors

    combined = pd.concat(all_jobs, ignore_index=True)
    return combined, errors


def filter_by_keywords(df: pd.DataFrame, must_contain: List[str] = None, must_not_contain: List[str] = None) -> pd.DataFrame:
    """
    Filter adicional client-side. Útil cuando keywords search no es preciso.

    Args:
        df: DataFrame de jobs
        must_contain: lista de strings, AL MENOS UNO debe estar en title o description
        must_not_contain: lista de strings, NINGUNO debe estar

    Returns:
        DataFrame filtered
    """
    if df.empty:
        return df

    if must_contain:
        pattern = "|".join([str(k).lower() for k in must_contain])
        mask = (
            df["title"].fillna("").str.lower().str.contains(pattern, regex=True, na=False)
            | df["description"].fillna("").str.lower().str.contains(pattern, regex=True, na=False)
        )
        df = df[mask]

    if must_not_contain:
        pattern = "|".join([str(k).lower() for k in must_not_contain])
        mask = ~(
            df["title"].fillna("").str.lower().str.contains(pattern, regex=True, na=False)
            | df["description"].fillna("").str.lower().str.contains(pattern, regex=True, na=False)
        )
        df = df[mask]

    return df


def filter_out_staffing_companies(
    df: pd.DataFrame,
    keyword_list: List[str],
    name_list: List[str],
) -> tuple:
    """Excluye empresas de staffing/recruiting (competidores de BRJ).

    Args:
        df: DataFrame con columna 'company'
        keyword_list: substrings que indican que la empresa ES una staffing agency
            (ej. 'staffing', 'recruiting', 'employment agency')
        name_list: nombres específicos a excluir (ej. 'adecco', 'robert half')

    Returns:
        (filtered_df, num_excluded, sample_excluded_names)
    """
    if df.empty or "company" not in df.columns:
        return df, 0, []

    company_lower = df["company"].fillna("").str.lower()

    # Mask: matchea cualquier keyword O cualquier nombre específico
    exclude_mask = pd.Series([False] * len(df), index=df.index)
    for kw in keyword_list:
        if kw:
            exclude_mask = exclude_mask | company_lower.str.contains(kw.lower(), case=False, na=False, regex=False)
    for name in name_list:
        if name:
            exclude_mask = exclude_mask | company_lower.str.contains(name.lower(), case=False, na=False, regex=False)

    excluded = df[exclude_mask]
    kept = df[~exclude_mask]
    sample = excluded["company"].fillna("").unique().tolist()[:10]
    return kept.reset_index(drop=True), len(excluded), sample


def dedup_by_company(df: pd.DataFrame) -> pd.DataFrame:
    """
    Una empresa puede tener N vacantes — quedate con la MÁS RECIENTE por company.

    Devuelve DataFrame con 1 fila por company + columna 'all_titles' agregada
    con la lista de TODAS las vacantes que tiene esa empresa.
    """
    if df.empty:
        return df

    df = df.copy()
    df["company_clean"] = df["company"].fillna("").str.lower().str.strip()

    # Agregar columna con todas las posiciones
    titles_per_company = (
        df.groupby("company_clean")["title"]
        .apply(lambda x: " | ".join(x.dropna().unique()))
        .to_dict()
    )

    # Tomar primera fila por empresa (la más reciente, asumiendo orden)
    deduped = df.drop_duplicates(subset=["company_clean"], keep="first").copy()
    deduped["all_titles"] = deduped["company_clean"].map(titles_per_company)
    deduped["vacancy_count"] = deduped["company_clean"].map(df["company_clean"].value_counts().to_dict())

    return deduped.drop(columns=["company_clean"])


# Job board domains que NO son sitios de empresas — filtrar para no usarlos como "company domain"
JOB_BOARD_DOMAIN_FRAGMENTS = (
    "indeed.com", "linkedin.com", "glassdoor.com", "ziprecruiter.com",
    "monster.com", "careerbuilder.com", "snagajob.com", "simplyhired.com",
    "google.com", "googleusercontent.com",
)


def _url_to_company_domain(url):
    """Convierte URL a dominio limpio. Devuelve None si el dominio es un job board."""
    if not url or pd.isna(url):
        return None
    try:
        s = str(url).strip()
        parsed = urlparse(s if s.startswith("http") else "https://" + s)
        netloc = parsed.netloc.replace("www.", "").lower()
        if not netloc or "." not in netloc:
            return None
        # Filtrar dominios de job boards
        for frag in JOB_BOARD_DOMAIN_FRAGMENTS:
            if frag in netloc:
                return None
        return netloc
    except Exception:
        return None


def _email_to_domain(emails_field):
    """Extrae dominio del primer email válido del field 'emails' de JobSpy (puede ser comma-separated)."""
    if not emails_field or pd.isna(emails_field):
        return None
    s = str(emails_field).strip()
    # Puede venir como "['a@x.com', 'b@y.com']" o "a@x.com, b@y.com" o "a@x.com"
    s = s.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    for email in s.split(","):
        email = email.strip()
        if "@" in email:
            domain = email.split("@", 1)[1].strip().lower()
            if "." in domain:
                # Skip job board domains aca tambien
                for frag in JOB_BOARD_DOMAIN_FRAGMENTS:
                    if frag in domain:
                        return None
                return domain
    return None


def extract_domain_from_company_url(df: pd.DataFrame) -> pd.DataFrame:
    """Extrae dominio REAL de la empresa.

    Estrategia (en orden de prioridad):
    1. company_url_direct (link directo al sitio de la empresa)
    2. company_url (a veces es el sitio, a veces el perfil del job board — filtramos los segundos)
    3. emails field (extraído del job description) → dominio del email
    """
    if df.empty:
        return df

    df = df.copy()
    n = len(df)
    domain_series = pd.Series([None] * n, index=df.index, dtype="object")

    # Strategy 1: company_url_direct
    if "company_url_direct" in df.columns:
        domain_series = df["company_url_direct"].apply(_url_to_company_domain)

    # Strategy 2: company_url (filtrando job boards)
    if "company_url" in df.columns:
        mask = domain_series.isna()
        fallback = df.loc[mask, "company_url"].apply(_url_to_company_domain)
        domain_series.loc[mask] = fallback

    # Strategy 3: emails field
    if "emails" in df.columns:
        mask = domain_series.isna()
        fallback = df.loc[mask, "emails"].apply(_email_to_domain)
        domain_series.loc[mask] = fallback

    df["company_domain"] = domain_series
    return df
