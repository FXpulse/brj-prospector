"""
usage.py - Tracking per-tenant de créditos consumidos por mes.

Lives en data/clients/<tenant>/usage.json:
{
  "2026-05": {
    "emails": 247,
    "phones": 18,
    "searches": 42,
    "first_use": "2026-05-01T14:23:00Z",
    "last_use": "2026-05-22T09:15:00Z"
  },
  "2026-04": {...}
}

Reset automático cada mes (key = YYYY-MM).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from lib.paths import get_tenant_usage_file, get_current_tenant
from lib.tiers import get_tier_limit, is_unlimited


def _current_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_usage(tenant):
    path = get_tenant_usage_file(tenant)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_usage(tenant, data):
    path = get_tenant_usage_file(tenant)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_usage(tenant=None, month=None):
    """Devuelve el usage dict del tenant para el mes indicado (default: este mes).

    Returns dict con keys: emails, phones, searches, first_use, last_use.
    """
    if tenant is None:
        tenant = get_current_tenant()
    if month is None:
        month = _current_month()

    all_usage = _load_usage(tenant)
    return all_usage.get(month, {
        "emails": 0,
        "phones": 0,
        "searches": 0,
        "first_use": None,
        "last_use": None,
    })


def record_usage(resource, count=1, tenant=None):
    """Incrementa el contador del recurso para este mes.

    resource: 'emails', 'phones', 'searches'
    """
    if tenant is None:
        tenant = get_current_tenant()

    month = _current_month()
    now = _now_iso()
    all_usage = _load_usage(tenant)
    monthly = all_usage.get(month, {
        "emails": 0,
        "phones": 0,
        "searches": 0,
        "first_use": now,
        "last_use": now,
    })
    monthly[resource] = monthly.get(resource, 0) + count
    monthly["last_use"] = now
    if not monthly.get("first_use"):
        monthly["first_use"] = now
    all_usage[month] = monthly
    _save_usage(tenant, all_usage)
    return monthly


def get_remaining(resource, tier, tenant=None, month=None):
    """Devuelve cuántos del recurso quedan este mes para este tenant + tier.

    Devuelve None si tier es unlimited.
    """
    if is_unlimited(tier):
        return None
    limit = get_tier_limit(tier, resource)
    used = get_usage(tenant, month).get(resource, 0)
    return max(0, limit - used)


def can_consume(resource, tier, count=1, tenant=None) -> bool:
    """True si el tenant todavía tiene cupo para consumir `count` de `resource`."""
    if is_unlimited(tier):
        return True
    remaining = get_remaining(resource, tier, tenant)
    return remaining is None or remaining >= count


def get_usage_history(tenant=None, months=6):
    """Devuelve usage de los últimos N meses, ordenado desc."""
    if tenant is None:
        tenant = get_current_tenant()
    all_usage = _load_usage(tenant)
    sorted_months = sorted(all_usage.keys(), reverse=True)[:months]
    return [(m, all_usage[m]) for m in sorted_months]


def list_all_tenants_usage(month=None):
    """Para el admin panel: devuelve usage del mes para TODOS los tenants.

    Returns: lista de dicts {tenant, emails, phones, searches, first_use, last_use}
    """
    if month is None:
        month = _current_month()

    from lib.paths import CLIENTS_DIR
    results = []
    if not CLIENTS_DIR.exists():
        return results

    for tenant_dir in CLIENTS_DIR.iterdir():
        if not tenant_dir.is_dir() or tenant_dir.name.startswith("_"):
            continue
        tenant = tenant_dir.name
        usage = get_usage(tenant=tenant, month=month)
        results.append({
            "tenant": tenant,
            **usage,
        })
    return results
