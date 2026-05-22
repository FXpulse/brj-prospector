"""
apollo_enrich.py - Wrapper de Apollo.io API para enrichment de decision-makers.

Apollo Basic plan: $69/mo, 2,500 credits/mes
- Email reveal: 1 credit
- Phone reveal: 8 credits

Endpoint principal: POST https://api.apollo.io/v1/mixed_people/search
Docs: https://docs.apollo.io/reference/people-search

Use case: dada una empresa (domain + industry), encontrar HR / Plant Manager
/ Operations decision-maker priorizando roles operacionales sobre C-suite.

Comparativa con Hunter:
- Apollo: data quality mejor, incluye phones, plan más barato ($69 vs Hunter $99)
- Hunter: pattern matching de emails, no phones, plan más caro
- Recomendación: Apollo como default cuando configurado, Hunter como fallback
"""
import json
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = SCRIPT_DIR / "data" / "_shared" / "apollo_cache.json"
CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

API_BASE = "https://api.apollo.io/v1"


def _load_cache():
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _api_key(cfg):
    return (cfg.get("apollo", {}) or {}).get("api_key", "")


def is_apollo_configured(cfg):
    key = _api_key(cfg)
    return bool(key and not key.startswith("PASTE"))


def search_people_at_domain(domain, cfg, titles=None, per_page=5, timeout=15):
    """Busca personas en una organización por domain + título priority.

    Args:
        domain: ej. "acmemfg.com"
        cfg: config dict con apollo.api_key
        titles: lista de títulos a priorizar (ej. ["recruiter", "HR manager", "talent acquisition"])
        per_page: cuántas personas devolver

    Returns:
        list of person dicts con keys: first_name, last_name, name, title, email, phone, organization
    """
    api_key = _api_key(cfg)
    if not api_key:
        return {"error": "no Apollo API key"}

    if not domain:
        return {"error": "no domain"}

    url = f"{API_BASE}/mixed_people/search"
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    body = {
        "q_organization_domains": domain,
        "page": 1,
        "per_page": per_page,
    }
    if titles:
        body["person_titles"] = titles

    try:
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        if r.status_code == 429:
            return {"error": "rate_limited", "details": "Apollo rate limit hit, retry later"}
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "details": r.text[:300]}
        data = r.json()
        return data.get("people", []) or []
    except requests.exceptions.Timeout:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}


def is_priority_role(position_str, priority_roles=None):
    """Check si el position matchea roles operacionales (HR, recruiter, ops, plant)."""
    if not position_str:
        return False
    if priority_roles is None:
        priority_roles = [
            "recruiter", "recruiting", "talent acquisition", "talent acquition",
            "hr coordinator", "hr specialist", "hr generalist", "hr manager",
            "hiring manager", "staffing coordinator", "supervisor",
            "plant manager", "operations manager", "operations director",
        ]
    pos = position_str.lower()
    return any(role in pos for role in priority_roles)


def _is_over_senior(position_str):
    """Detecta roles C-suite / VP / President que NO queremos para staffing pitch."""
    if not position_str:
        return False
    pos = position_str.lower()
    over_senior = [
        "ceo", "chief executive", "chief operating", "coo", "chief financial", "cfo",
        "chief technology", "cto", "chief", "president", "vp", "vice president",
        "founder", "owner",
    ]
    return any(k in pos for k in over_senior)


def find_decision_maker_at_domain(domain, cfg, priority_roles=None):
    """Encuentra el mejor decision-maker en la empresa, con priority de roles
    operacionales sobre C-suite.

    Returns dict: {first_name, last_name, position, email, phone, is_priority_role,
                   confidence, organization, error?}
    """
    if not domain:
        return {"error": "no domain"}

    cache = _load_cache()
    cache_key = f"{domain}__dm"
    if cache_key in cache:
        return {**cache[cache_key], "from_cache": True}

    # Build title priority list (passed-in OR default)
    if not priority_roles:
        priority_roles = [
            "recruiter", "recruiting", "talent acquisition",
            "hr coordinator", "hr specialist", "hr generalist",
            "hiring manager", "staffing coordinator",
            "supervisor", "hr manager",
        ]

    # Apollo search — solicit people with these titles at this domain
    people = search_people_at_domain(domain, cfg, titles=priority_roles, per_page=5)

    if isinstance(people, dict) and people.get("error"):
        # Pass through error
        return people

    if not people:
        result = {"error": "no_results"}
        cache[cache_key] = result
        _save_cache(cache)
        return result

    # Score each person — prefer those matching priority roles, skip over-seniors
    def score(p):
        pos = (p.get("title") or "").lower()
        if is_priority_role(pos, priority_roles):
            return 0
        if _is_over_senior(pos):
            return 9
        if any(k in pos for k in ["director", "manager", "head", "lead"]):
            return 1
        return 2

    people_sorted = sorted(people, key=score)
    best = people_sorted[0]
    best_score = score(best)

    if best_score == 9:
        result = {"error": "only over-senior contacts found (CEO/VP/President) — skipped"}
        cache[cache_key] = result
        _save_cache(cache)
        return result

    org = best.get("organization", {}) or {}
    result = {
        "first_name": best.get("first_name", ""),
        "last_name": best.get("last_name", ""),
        "name": best.get("name", ""),
        "position": best.get("title", ""),
        "email": best.get("email", "") or "",
        "phone": "",  # Apollo phones require a separate /v1/people/match call with $$$
        "is_priority_role": best_score == 0,
        "confidence": best.get("email_status", "") or "",
        "organization": org.get("name", ""),
        "linkedin_url": best.get("linkedin_url", ""),
        "apollo_id": best.get("id", ""),
        "_source": "apollo",
    }

    cache[cache_key] = result
    _save_cache(cache)
    return result


def get_apollo_usage(cfg):
    """Devuelve credits usage info de Apollo si la API key permite consultarlo.

    Apollo no expone un endpoint público estable para 'credits remaining'.
    Esta función devuelve un placeholder — el real tracking lo hacemos en lib/usage.py
    via record_usage("emails", 1) cuando se hace un lookup.
    """
    if not is_apollo_configured(cfg):
        return None
    return {
        "configured": True,
        "monthly_limit": 2500,  # Basic plan
        "note": "Track usage via lib/usage.py — Apollo doesn't expose remaining count via API",
    }
