"""
domain_lookup.py - Resuelve el dominio REAL de una empresa cuando JobSpy
no lo trae directo.

Pipeline de lookup:
  1. company_url_direct (de JobSpy) — primary
  2. Scrape Indeed company profile → extraer "Visit website" link
  3. Google Custom Search API → buscar nombre + filtrar job boards
  4. Domain from emails field (fallback final)

Todo cacheado en data/domain_cache.json para no repetir lookups.
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests


def _safe_str(val):
    """Devuelve string limpio incluso si val es None, NaN, float, etc."""
    if val is None:
        return ""
    try:
        if isinstance(val, float) and pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    if s.lower() in ("nan", "none", "<na>", "null"):
        return ""
    return s

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = SCRIPT_DIR / "data" / "domain_cache.json"

JOB_BOARD_DOMAINS = (
    "indeed.com", "linkedin.com", "glassdoor.com", "ziprecruiter.com",
    "monster.com", "careerbuilder.com", "snagajob.com", "simplyhired.com",
    "google.com", "googleusercontent.com", "facebook.com", "twitter.com",
    "youtube.com", "yelp.com", "bbb.org", "yellowpages.com", "manta.com",
    "wikipedia.org", "instagram.com", "tiktok.com", "pinterest.com",
)


def _load_cache():
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _url_to_clean_domain(url):
    """URL → clean domain, None si es job board o invalid."""
    s = _safe_str(url)
    if not s:
        return None
    try:
        parsed = urlparse(s if s.startswith("http") else "https://" + s)
        netloc = parsed.netloc.replace("www.", "").lower()
        if not netloc or "." not in netloc:
            return None
        for jb in JOB_BOARD_DOMAINS:
            if jb in netloc:
                return None
        return netloc
    except Exception:
        return None


# ─── Strategy 2: Scrape Indeed company profile ──────────────────
INDEED_WEBSITE_PATTERNS = [
    # Pattern 1: explicit "Visit website" link
    re.compile(r'href="(https?://[^"]+)"[^>]*[^<]*>\s*(?:Visit website|Company website|Website)\s*<', re.I),
    # Pattern 2: data-tn-element attribute
    re.compile(r'data-tn-element="[^"]*website[^"]*"[^>]*href="(https?://[^"]+)"', re.I),
    re.compile(r'href="(https?://[^"]+)"[^>]*data-tn-element="[^"]*website[^"]*"', re.I),
    # Pattern 3: JSON-LD structured data
    re.compile(r'"@type"\s*:\s*"Organization"[^}]*"url"\s*:\s*"(https?://[^"]+)"', re.I),
    re.compile(r'"url"\s*:\s*"(https?://[^"]+)"[^}]*"@type"\s*:\s*"Organization"', re.I),
    # Pattern 4: "About us" section with external link
    re.compile(r'About us[^<]*</[^>]+>\s*<[^>]+href="(https?://[^"]+)"', re.I),
]


def scrape_indeed_profile_for_website(indeed_url, timeout=8):
    """Visita un Indeed company profile y devuelve el website real."""
    indeed_url = _safe_str(indeed_url)
    if not indeed_url or "indeed.com/cmp" not in indeed_url:
        return None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        r = requests.get(str(indeed_url), headers=headers, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return None
        html = r.text[:300000]  # cap

        for pattern in INDEED_WEBSITE_PATTERNS:
            for m in pattern.finditer(html):
                url = m.group(1)
                domain = _url_to_clean_domain(url)
                if domain:
                    return domain
    except Exception:
        return None
    return None


# ─── Strategy 3: Google Custom Search ───────────────────────────
def google_search_company_website(company_name, location_hint, cfg):
    """Busca el website oficial via Google Custom Search API.

    Requiere en config: google_cse.api_key + google_cse.cse_id
    Free tier: 100 queries/day
    """
    g_cfg = cfg.get("google_cse", {})
    api_key = g_cfg.get("api_key", "")
    cse_id = g_cfg.get("cse_id", "")
    if not api_key or api_key.startswith("PASTE") or not cse_id or cse_id.startswith("PASTE"):
        return None
    if not company_name:
        return None

    query_parts = [company_name.strip()]
    if location_hint:
        query_parts.append(location_hint.strip())
    query_parts.append("official website")
    query = " ".join(query_parts)

    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cse_id, "q": query, "num": 5}

    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return None
        items = r.json().get("items", []) or []
        for item in items:
            link = item.get("link", "")
            domain = _url_to_clean_domain(link)
            if domain:
                return domain
    except Exception:
        return None
    return None


# ─── Strategy 4: Email field fallback ───────────────────────────
def email_field_to_domain(emails_field):
    s = _safe_str(emails_field)
    if not s:
        return None
    s = s.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    for email in s.split(","):
        email = email.strip()
        if "@" in email:
            domain = email.split("@", 1)[1].strip().lower()
            if "." in domain:
                for jb in JOB_BOARD_DOMAINS:
                    if jb in domain:
                        return None
                return domain
    return None


# ─── Orchestrator ───────────────────────────────────────────────
def resolve_company_domain(
    row,
    cfg,
    use_indeed_scrape=True,
    use_google_search=True,
    cache=None,
):
    """Aplica el pipeline completo para encontrar el dominio real.

    Returns:
        (domain, source) — source: 'direct', 'company_url', 'indeed_scrape', 'google', 'email', None
    """
    company = _safe_str(row.get("company"))
    if not company:
        return None, None

    cache_key = company.lower()
    if cache is not None and cache_key in cache:
        cached = cache[cache_key]
        return cached.get("domain"), cached.get("source", "cache")

    # Strategy 1: company_url_direct
    domain = _url_to_clean_domain(row.get("company_url_direct"))
    if domain:
        if cache is not None:
            cache[cache_key] = {"domain": domain, "source": "direct"}
        return domain, "direct"

    # Strategy 2: company_url (filtrando job boards)
    domain = _url_to_clean_domain(row.get("company_url"))
    if domain:
        if cache is not None:
            cache[cache_key] = {"domain": domain, "source": "company_url"}
        return domain, "company_url"

    # Strategy 3: Indeed profile scrape
    if use_indeed_scrape:
        company_url = _safe_str(row.get("company_url"))
        if company_url and "indeed.com/cmp" in company_url:
            domain = scrape_indeed_profile_for_website(company_url)
            if domain:
                if cache is not None:
                    cache[cache_key] = {"domain": domain, "source": "indeed_scrape"}
                return domain, "indeed_scrape"

    # Strategy 4: Google Custom Search
    if use_google_search and company:
        location = _safe_str(row.get("location")) or _safe_str(row.get("search_location"))
        loc_clean = location.split(",")[0:2] if location else []
        loc_str = " ".join([s.strip() for s in loc_clean]).strip()

        domain = google_search_company_website(company, loc_str, cfg)
        if domain:
            if cache is not None:
                cache[cache_key] = {"domain": domain, "source": "google"}
            return domain, "google"

    # Strategy 5: emails field
    domain = email_field_to_domain(row.get("emails"))
    if domain:
        if cache is not None:
            cache[cache_key] = {"domain": domain, "source": "email"}
        return domain, "email"

    # Nothing worked
    if cache is not None:
        cache[cache_key] = {"domain": None, "source": None}
    return None, None


def enrich_domains_in_dataframe(
    df,
    cfg,
    use_indeed_scrape=True,
    use_google_search=False,
    progress_cb=None,
):
    """Aplica resolve_company_domain a todo un DataFrame.

    Devuelve el df con columnas nuevas: company_domain, domain_source
    También guarda el cache.
    """
    if df.empty:
        return df

    cache = _load_cache()
    df = df.copy()

    domains = []
    sources = []
    for i, row in enumerate(df.to_dict("records")):
        domain, source = resolve_company_domain(
            row, cfg,
            use_indeed_scrape=use_indeed_scrape,
            use_google_search=use_google_search,
            cache=cache,
        )
        domains.append(domain)
        sources.append(source or "")

        if progress_cb:
            progress_cb(i + 1, len(df), row.get("company"), domain, source)

        # Save cache periodicamente
        if (i + 1) % 10 == 0:
            _save_cache(cache)

        # Rate limit polite
        if source in ("indeed_scrape", "google"):
            time.sleep(0.3)

    df["company_domain"] = domains
    df["domain_source"] = sources

    _save_cache(cache)
    return df
