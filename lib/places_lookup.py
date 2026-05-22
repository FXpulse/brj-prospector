"""
places_lookup.py - Google Places API para conseguir phone + address de una empresa
por nombre + ubicación.

Free tier: $200/mes Google Cloud credit → ~11,000 lookups/mes sin pagar.
Same API key que Google CSE (Custom Search API).

Cache local en data/places_cache.json.
"""
import json
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = SCRIPT_DIR / "data" / "places_cache.json"


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


def search_company_in_places(company_name, location_hint, cfg, timeout=8):
    """Busca la empresa en Google Places y devuelve phone + address.

    Args:
        company_name: nombre de la empresa
        location_hint: city + state (ej. "Jacksonville FL")
        cfg: config dict con google_cse.api_key (mismo key sirve para Places)
        timeout: HTTP timeout

    Returns:
        {phone, address, website, rating, num_reviews} o {} si no se encuentra.
    """
    if not company_name:
        return {}

    api_key = cfg.get("google_cse", {}).get("api_key", "")
    if not api_key or api_key.startswith("PASTE"):
        return {"error": "no Google API key"}

    query = f"{company_name} {location_hint or ''}".strip()

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,"
            "places.nationalPhoneNumber,places.internationalPhoneNumber,"
            "places.websiteUri,places.rating,places.userRatingCount,"
            "places.businessStatus"
        ),
        "Content-Type": "application/json",
    }
    body = {"textQuery": query, "pageSize": 1}

    try:
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "details": r.text[:200]}
        data = r.json()
        places = data.get("places", [])
        if not places:
            return {}

        p = places[0]
        # Skip si está cerrado / no operacional
        if p.get("businessStatus") and p.get("businessStatus") != "OPERATIONAL":
            return {"status_not_operational": True}

        return {
            "phone": p.get("internationalPhoneNumber") or p.get("nationalPhoneNumber") or "",
            "address": p.get("formattedAddress") or "",
            "website": p.get("websiteUri") or "",
            "rating": p.get("rating", 0),
            "reviews_count": p.get("userRatingCount", 0),
            "google_name": (p.get("displayName") or {}).get("text", ""),
        }
    except Exception as e:
        return {"error": str(e)}


def get_company_phone(company_name, location_hint, cfg, cache=None):
    """Wrapper con cache. Si no hay phone, retorna ''. Cache key: company_name lowercase."""
    if not company_name:
        return ""
    cache_key = company_name.strip().lower()

    if cache is None:
        cache = _load_cache()

    if cache_key in cache:
        return cache[cache_key].get("phone", "")

    result = search_company_in_places(company_name, location_hint, cfg)
    cache[cache_key] = result
    _save_cache(cache)
    return result.get("phone", "")


def enrich_phones_in_dataframe(df, cfg, company_col="company", location_col="location", progress_cb=None):
    """Agrega columna 'company_phone' al DataFrame.

    Reutiliza cache local — no quema Google quota si la empresa ya fue queryeada.
    """
    if df.empty or company_col not in df.columns:
        df["company_phone"] = ""
        return df

    cache = _load_cache()
    phones = []

    for i, row in enumerate(df.to_dict("records")):
        company = row.get(company_col) or ""
        location = row.get(location_col) or ""

        if not company or company.strip() == "" or str(company).lower() == "nan":
            phones.append("")
            if progress_cb:
                progress_cb(i + 1, len(df), "?", "")
            continue

        cache_key = str(company).strip().lower()
        if cache_key in cache:
            phone = cache[cache_key].get("phone", "")
            phones.append(phone)
            if progress_cb:
                progress_cb(i + 1, len(df), company, phone + " [cache]")
            continue

        # Reducir location a city para mejor matching
        loc_clean = str(location).split(",")[0:2] if location else []
        loc_str = " ".join([s.strip() for s in loc_clean]).strip()

        result = search_company_in_places(company, loc_str, cfg)
        cache[cache_key] = result
        phone = result.get("phone", "")
        phones.append(phone)
        # Per-tenant usage tracking (counted only on actual API call, not cache hit)
        if phone:
            try:
                from lib.usage import record_usage
                record_usage("phones", 1)
            except Exception:
                pass

        if progress_cb:
            progress_cb(i + 1, len(df), company, phone or "(no phone)")

        # Save cache periodically
        if (i + 1) % 10 == 0:
            _save_cache(cache)

        # Rate limit polite
        time.sleep(0.1)

    _save_cache(cache)
    df = df.copy()
    df["company_phone"] = phones
    return df
