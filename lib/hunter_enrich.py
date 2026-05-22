"""
hunter_enrich.py - Hunter.io enrichment focused on finding RECRUITERS / HR contacts
at target companies.

Use case BRJ: por cada vacante encontrada en job boards, queremos el nombre y email
del recruiter / talent acquisition / HR manager de la empresa que postea.
"""
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone

import requests
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = SCRIPT_DIR / "data" / "hunter_cache.json"
CREDITS_FILE = SCRIPT_DIR / "data" / "hunter_credits.json"


def load_config():
    """Reexport del loader centralizado para backward compat."""
    from lib.config_loader import load_config as _load_config
    return _load_config()


def _load_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _current_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def load_credits_state():
    state = _load_json(CREDITS_FILE, {"month": _current_month(), "used": 0})
    if state.get("month") != _current_month():
        state = {"month": _current_month(), "used": 0}
    return state


def save_credits_state(state):
    _save_json(CREDITS_FILE, state)


def hunter_credits_remaining(cfg=None):
    """Devuelve cuántos credits Hunter quedan este mes."""
    if cfg is None:
        cfg = load_config()
    limit = cfg.get("hunter", {}).get("monthly_limit", 1000)
    state = load_credits_state()
    return max(0, limit - state.get("used", 0))


def domain_from_url(url):
    if not url or not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url if url.startswith("http") else "https://" + url)
        d = parsed.netloc.replace("www.", "").lower()
        return d if d and "." in d else None
    except Exception:
        return None


def is_recruiter_position(position, cfg):
    """True si el position parece un rol de recruiting/HR."""
    if not position:
        return False
    p = position.lower()
    recruiter_kws = cfg.get("brj_specific", {}).get("recruiter_role_keywords", [])
    exclude_kws = cfg.get("brj_specific", {}).get("exclude_role_keywords", [])

    if any(ex in p for ex in exclude_kws):
        return False
    return any(kw in p for kw in recruiter_kws)


def find_recruiter_at_domain(domain, cfg):
    """Pipeline A: prioriza roles de recruiting/HR para encontrar el recruiter
    de la empresa que postea las vacantes."""
    priority_roles = cfg.get("brj_specific", {}).get("recruiter_role_keywords", [])
    # Wrap is_recruiter_position con closure para que solo reciba `pos`
    return _hunter_find_with_role_priority(
        domain, cfg, priority_roles,
        role_check_fn=lambda pos: is_recruiter_position(pos, cfg),
    )


def find_decision_maker_at_domain(domain, cfg, priority_roles=None):
    """Pipeline B: prioriza recruiters/HR coordinators/supervisores que toman
    decisiones operacionales de staffing — NO C-suite, NO VPs.

    Lógica: el que maneja staffing day-to-day es quien mira hiring volume,
    no el CEO. Recruiter + HR Coordinator + Supervisor = sweet spot.

    priority_roles: lista de keywords de roles a priorizar (override del default).
    """
    if not priority_roles:
        priority_roles = [
            "recruiter", "recruiting", "talent acquisition",
            "hr coordinator", "hr specialist", "hr generalist",
            "hiring manager", "staffing coordinator",
            "supervisor",  # planta level
            "hr manager",  # último recurso
        ]

    def is_decision_maker(pos):
        if not pos:
            return False
        p = pos.lower()
        return any(k.lower() in p for k in priority_roles)

    return _hunter_find_with_role_priority(
        domain, cfg, priority_roles,
        role_check_fn=is_decision_maker,
    )


def _hunter_find_with_role_priority(domain, cfg, priority_roles, role_check_fn):
    """Internal: query Hunter + priorizar emails por role match.

    role_check_fn(position_string) → True si es priority.
    """
    api_key = cfg.get("hunter", {}).get("api_key")
    if not api_key or api_key.startswith("PASTE"):
        return {"error": "no Hunter API key in config"}

    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": 25,
        "type": "personal",
    }

    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "details": r.text[:200]}
        data = r.json().get("data", {})
        emails = data.get("emails", []) or []
    except Exception as e:
        return {"error": str(e)}

    if not emails:
        return {}

    def score(e):
        pos = (e.get("position") or "").lower()
        # Score 0 = priority role (best)
        if role_check_fn(pos):
            return 0
        # PENALTY: roles over-senior. Estos NO manejan staffing day-to-day.
        # Los descartamos al final aunque tengamos data.
        OVER_SENIOR = ["ceo", "chief executive", "chief operating", "coo", "chief",
                       "president", "vp", "vice president", "founder", "owner"]
        if any(k in pos for k in OVER_SENIOR):
            return 9  # worst — descartar si hay alternativa
        # Score 1 = roles managerial OK (Director, Manager, Lead)
        if any(k in pos for k in ["director", "manager", "head", "lead"]):
            return 1
        # Score 2 = cualquier otro role
        return 2

    emails_sorted = sorted(emails, key=score)
    best = emails_sorted[0]
    best_score = score(best)

    # Si el mejor todavía es over-senior (score=9), no lo retornamos
    if best_score == 9:
        return {"reason": "only over-senior contacts found (CEO/VP/President) — skipped"}

    # Phone: Hunter a veces retorna phone_number en el email object
    dm_phone = ""
    if best.get("phone_number"):
        dm_phone = best["phone_number"]

    return {
        "first_name": best.get("first_name", ""),
        "last_name": best.get("last_name", ""),
        "email": best.get("value", ""),
        "position": best.get("position", ""),
        "phone": dm_phone,
        "confidence": best.get("confidence", 0),
        "is_priority_role": best_score == 0,
        "is_recruiter_role": best_score == 0,  # backward compat con Pipeline A
    }


def lookup_with_cache(domain, cfg, credits_state):
    """Lookup con cache local + global Hunter limit + per-tenant tier enforcement."""
    if not domain:
        return {}

    cache = _load_json(CACHE_FILE, {})
    if domain in cache:
        return {**cache[domain], "from_cache": True}

    # Check global Hunter limit (la cuota total del API)
    limit = cfg.get("hunter", {}).get("monthly_limit", 1000)
    if credits_state.get("used", 0) >= limit:
        return {"error": "Hunter monthly limit reached"}

    # Check per-tenant tier limit (Starter / Pro / Custom)
    try:
        from lib.usage import can_consume
        from lib.paths import get_current_tier
        tier = get_current_tier()
        if not can_consume("emails", tier, 1):
            return {"error": "tier_limit_reached", "resource": "emails"}
    except Exception:
        pass  # si falla, no bloquear

    result = find_recruiter_at_domain(domain, cfg)
    if not result.get("error"):
        credits_state["used"] = credits_state.get("used", 0) + 1
        save_credits_state(credits_state)
        try:
            from lib.usage import record_usage
            record_usage("emails", 1)
        except Exception:
            pass

    cache[domain] = result
    _save_json(CACHE_FILE, cache)
    return result


def enrich_dataframe(df, cfg=None, domain_col="company_domain", progress_cb=None, max_lookups=None):
    """Enriquece un DataFrame con info de recruiter de cada empresa.

    Args:
        df: DataFrame con al menos una columna 'company_domain'
        cfg: config dict (auto-loaded si None)
        domain_col: nombre de la columna que tiene los dominios
        progress_cb: callback(i, total, domain, result) para UI updates
        max_lookups: limit hard a cuántos Hunter calls hacer (None = unlimited dentro del monthly limit)

    Returns:
        DataFrame con columnas adicionales:
        - recruiter_first_name, recruiter_last_name, recruiter_email,
          recruiter_position, recruiter_confidence, recruiter_is_priority,
          hunter_from_cache, hunter_error
    """
    if cfg is None:
        cfg = load_config()

    if df.empty or domain_col not in df.columns:
        return df

    credits_state = load_credits_state()
    df = df.copy()

    new_cols = {
        "recruiter_first_name": [],
        "recruiter_last_name": [],
        "recruiter_email": [],
        "recruiter_position": [],
        "recruiter_confidence": [],
        "recruiter_is_priority": [],
        "hunter_from_cache": [],
        "hunter_error": [],
    }

    lookups_done = 0
    for i, row in enumerate(df.itertuples(index=False)):
        domain = getattr(row, domain_col, None) if hasattr(row, domain_col) else None

        if not domain:
            for k in new_cols:
                new_cols[k].append("")
            if progress_cb:
                progress_cb(i + 1, len(df), None, {"skipped": "no domain"})
            continue

        if max_lookups is not None and lookups_done >= max_lookups:
            for k in new_cols:
                new_cols[k].append("")
            new_cols["hunter_error"][-1] = "skipped (max_lookups reached)"
            continue

        result = lookup_with_cache(domain, cfg, credits_state)
        if not result.get("from_cache"):
            lookups_done += 1

        new_cols["recruiter_first_name"].append(result.get("first_name", ""))
        new_cols["recruiter_last_name"].append(result.get("last_name", ""))
        new_cols["recruiter_email"].append(result.get("email", ""))
        new_cols["recruiter_position"].append(result.get("position", ""))
        new_cols["recruiter_confidence"].append(result.get("confidence", ""))
        new_cols["recruiter_is_priority"].append(result.get("is_recruiter_role", False))
        new_cols["hunter_from_cache"].append(result.get("from_cache", False))
        new_cols["hunter_error"].append(result.get("error", ""))

        if progress_cb:
            progress_cb(i + 1, len(df), domain, result)

        # Light rate limit
        if not result.get("from_cache") and not result.get("error"):
            time.sleep(0.1)

    for col, vals in new_cols.items():
        if len(vals) == len(df):
            df[col] = vals
        else:
            # Padding si por alguna razón hubo diferencia (no debería pasar)
            df[col] = vals + [""] * (len(df) - len(vals))

    return df
