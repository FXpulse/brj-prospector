"""
ghl_status.py - Wrapper de GHL API para verificar status de cliente.

Architectura: source of truth para "is this customer paid + what tier" vive
en GHL. Prospector hace lookup en cada login para grant/deny access.

Config esperado:
{
  "ghl": {
    "pit": "pit-...",
    "location_id": "...",
    "base_url": "https://services.leadconnectorhq.com",
    "api_version": "2021-07-28"
  }
}

Custom fields en GHL Contact que leemos:
- prospector_tier (dropdown: starter/pro/custom)
- prospector_tenant (text)
- prospector_status (dropdown: active/trial/paused/cancelled)

Tags en GHL Contact:
- paid-customer = acceso completo según tier
- trial = acceso limitado (Starter limits)
- cancelled / paused = acceso bloqueado
"""
import json
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = SCRIPT_DIR / "data" / "_shared" / "ghl_status_cache.json"
CACHE_TTL_SEC = 300  # 5 min cache para evitar API spam en logins frecuentes


def _now():
    return int(time.time())


def _load_cache():
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def is_ghl_configured(cfg):
    ghl = cfg.get("ghl") or {}
    pit = ghl.get("pit", "")
    loc = ghl.get("location_id", "")
    return bool(pit and pit.startswith("pit-") and loc and not loc.startswith("PASTE"))


def lookup_contact_by_email(email, cfg, use_cache=True):
    """Busca un GHL contact por email. Devuelve raw contact dict o {error}.

    Cache local 5 min para evitar API spam en sessiones con muchos reruns.
    """
    if not email:
        return {"error": "no_email"}
    if not is_ghl_configured(cfg):
        return {"error": "ghl_not_configured"}

    cache = _load_cache()
    cache_key = email.lower().strip()

    if use_cache and cache_key in cache:
        entry = cache[cache_key]
        if _now() - entry.get("at", 0) < CACHE_TTL_SEC:
            return {**entry["data"], "from_cache": True}

    ghl = cfg["ghl"]
    base = ghl.get("base_url", "https://services.leadconnectorhq.com")
    version = ghl.get("api_version", "2021-07-28")
    location_id = ghl["location_id"]
    pit = ghl["pit"]

    url = f"{base}/contacts/"
    headers = {
        "Authorization": f"Bearer {pit}",
        "Version": version,
        "Accept": "application/json",
    }
    params = {
        "locationId": location_id,
        "query": email,
        "limit": 1,
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return {"error": f"http_{r.status_code}", "details": r.text[:200]}
        data = r.json() or {}
        contacts = data.get("contacts") or []
        if not contacts:
            return {"error": "contact_not_found"}

        contact = contacts[0]
        # Cache it
        cache[cache_key] = {"at": _now(), "data": contact}
        _save_cache(cache)
        return contact
    except requests.exceptions.Timeout:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}


def _extract_custom_field(contact, field_key):
    """Lee un custom field por su key/name. GHL los devuelve como lista de objetos."""
    cfs = contact.get("customFields") or contact.get("custom_fields") or []
    for cf in cfs:
        # GHL puede usar 'fieldKey', 'key', 'name', o 'id'
        candidates = [
            cf.get("fieldKey", ""),
            cf.get("key", ""),
            cf.get("name", ""),
            cf.get("field_key", ""),
        ]
        if field_key in candidates or field_key.lower() in [c.lower() for c in candidates]:
            return cf.get("value") or cf.get("field_value") or ""
    return ""


def verify_contact_status(email, cfg):
    """Devuelve el status enriquecido del contact para decidir access.

    Returns dict:
    {
        "ok": bool,
        "access_granted": bool,
        "reason": str (si denied, motivo),
        "tier": str (starter/pro/custom),
        "tenant": str (slug),
        "tags": list,
        "contact_id": str,
    }
    """
    contact = lookup_contact_by_email(email, cfg)
    if "error" in contact:
        return {
            "ok": False,
            "access_granted": False,
            "reason": f"GHL lookup failed: {contact.get('error')}",
            "tier": "starter",
            "tenant": "default",
            "tags": [],
        }

    tags = [t.lower() for t in (contact.get("tags") or [])]

    has_paid_tag = "paid-customer" in tags
    has_trial_tag = "trial" in tags
    has_cancelled_tag = "cancelled" in tags
    has_paused_tag = "paused" in tags

    # Custom fields
    tier = (_extract_custom_field(contact, "prospector_tier") or "").lower().strip() or "starter"
    tenant = (_extract_custom_field(contact, "prospector_tenant") or "").strip() or "default"
    status_field = (_extract_custom_field(contact, "prospector_status") or "").lower().strip()

    # Decision logic
    if has_cancelled_tag or status_field == "cancelled":
        return {
            "ok": True,
            "access_granted": False,
            "reason": "Your account was cancelled. Email hello@theprospector.io to reactivate.",
            "tier": tier,
            "tenant": tenant,
            "tags": tags,
            "contact_id": contact.get("id"),
        }
    if has_paused_tag or status_field == "paused":
        return {
            "ok": True,
            "access_granted": False,
            "reason": "Your account is paused (likely billing issue). Email hello@theprospector.io.",
            "tier": tier,
            "tenant": tenant,
            "tags": tags,
            "contact_id": contact.get("id"),
        }
    if not (has_paid_tag or has_trial_tag):
        return {
            "ok": True,
            "access_granted": False,
            "reason": "No active subscription found. Email hello@theprospector.io to start your trial.",
            "tier": tier,
            "tenant": tenant,
            "tags": tags,
            "contact_id": contact.get("id"),
        }

    # Active
    return {
        "ok": True,
        "access_granted": True,
        "reason": "active",
        "tier": tier if tier in ("starter", "pro", "custom") else "starter",
        "tenant": tenant if tenant != "default" else email.split("@")[0],
        "tags": tags,
        "contact_id": contact.get("id"),
    }
