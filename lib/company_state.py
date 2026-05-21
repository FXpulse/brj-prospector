"""
company_state.py - Tracking persistente de empresas vistas + contactadas.

Evita:
- Re-procesar (resolve domain, Hunter lookup) empresas ya conocidas → ahorra credits
- Re-mostrar a BRJ empresas que ya contactaron → no saturar prospects
- Perder histórico de qué se buscó cuándo

State file: data/company_state.json
"""
import json
import re
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = SCRIPT_DIR / "data" / "company_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# Sufijos corporativos a quitar para normalizar nombre
CORPORATE_SUFFIXES = [
    " inc", " inc.", " llc", " l.l.c.", " corp", " corp.", " corporation",
    " co", " co.", " company", " ltd", " ltd.", " limited",
    " group", " holdings", " enterprises",
]


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_company_key(company_name, location=""):
    """Construye una key estable para identificar la empresa.

    Combina nombre normalizado + city (primer chunk de la location).
    Permite distinguir entre "Acme Manufacturing - Jacksonville" y "Acme Manufacturing - Dallas".
    """
    if not company_name:
        return ""

    name = str(company_name).lower().strip()
    # Quitar puntuación común
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    # Quitar sufijos corporativos (al final)
    for suffix in CORPORATE_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
            break

    name = name.replace(" ", "_")

    # City normalization
    city = ""
    if location:
        loc_str = str(location).split(",")[0].lower()
        city = re.sub(r"[^a-z0-9]", "", loc_str)

    return f"{name}__{city}" if city else name


def load_state():
    """Carga state.json, devuelve dict vacío si no existe."""
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(state):
    """Persiste state.json."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def get_company_status(state, company_name, location=""):
    """Devuelve dict del status de una empresa: NEW / IN_DB / CONTACTED.

    Returns:
        {"status": "NEW"|"IN_DB"|"CONTACTED", "data": existing_record_or_None}
    """
    key = normalize_company_key(company_name, location)
    if not key:
        return {"status": "NEW", "data": None}

    record = state.get(key)
    if not record:
        return {"status": "NEW", "data": None}

    if record.get("contacted"):
        return {"status": "CONTACTED", "data": record}

    return {"status": "IN_DB", "data": record}


def upsert_company(state, company_name, location="", **extras):
    """Crea o actualiza el registro de una empresa.

    extras puede incluir: domain, decision_maker (dict), industries, queries_matched (list),
    vacancy_count, etc. NO sobreescribe contact_date, contacted, notes (esos son user-editable).
    """
    key = normalize_company_key(company_name, location)
    if not key:
        return state

    existing = state.get(key, {})
    now = _now_iso()

    record = {
        "company_name": company_name,
        "location": location,
        "first_seen": existing.get("first_seen", now),
        "last_seen": now,
        "appearances": existing.get("appearances", 0) + 1,
        "contacted": existing.get("contacted", False),
        "contact_date": existing.get("contact_date"),
        "notes": existing.get("notes", ""),
    }

    # Industries: merge unique
    industries_old = set(existing.get("industries_seen", []) or [])
    industries_new = set(extras.get("industries", []) or [])
    industries_merged = sorted(industries_old | industries_new)
    if industries_merged:
        record["industries_seen"] = industries_merged

    # Queries matched: merge unique
    queries_old = set(existing.get("queries_matched", []) or [])
    queries_new = set(extras.get("queries_matched", []) or [])
    queries_merged = sorted(queries_old | queries_new)
    if queries_merged:
        record["queries_matched"] = queries_merged[:30]  # cap

    # Domain: keep first non-empty
    domain = extras.get("domain") or existing.get("domain")
    if domain:
        record["domain"] = domain

    # Decision maker: prefer current if has email
    dm = extras.get("decision_maker") or existing.get("decision_maker") or {}
    if dm.get("email"):
        record["decision_maker"] = dm
    elif existing.get("decision_maker", {}).get("email"):
        record["decision_maker"] = existing["decision_maker"]

    # Latest vacancy count (per run)
    if "vacancy_count" in extras:
        record["last_vacancy_count"] = extras["vacancy_count"]
        record["max_vacancy_count"] = max(
            existing.get("max_vacancy_count", 0),
            extras["vacancy_count"],
        )

    state[key] = record
    return state


def mark_as_contacted(state, company_name, location="", note=""):
    """Marca una empresa como contactada."""
    key = normalize_company_key(company_name, location)
    if not key or key not in state:
        return state
    state[key]["contacted"] = True
    state[key]["contact_date"] = _now_iso()
    if note:
        state[key]["notes"] = (state[key].get("notes", "") + "\n" + note).strip()
    return state


def mark_many_as_contacted(state, items, note=""):
    """items: lista de tuples (company_name, location)"""
    for company_name, location in items:
        state = mark_as_contacted(state, company_name, location, note=note)
    return state


def get_stats(state):
    """Estadísticas globales del state."""
    total = len(state)
    contacted = sum(1 for r in state.values() if r.get("contacted"))
    in_db = total - contacted
    with_domain = sum(1 for r in state.values() if r.get("domain"))
    with_dm = sum(1 for r in state.values() if r.get("decision_maker", {}).get("email"))
    return {
        "total_companies": total,
        "contacted": contacted,
        "in_db_not_contacted": in_db,
        "with_domain": with_domain,
        "with_decision_maker": with_dm,
    }
