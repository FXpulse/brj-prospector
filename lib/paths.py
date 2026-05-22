"""
paths.py - Tenant-aware path helpers.

Data layout:

    data/
    ├── _shared/                  ← caches que se comparten entre tenants
    │   ├── hunter_cache.json     ← lookups por domain (mismo domain = misma respuesta)
    │   └── places_cache.json     ← Google Places lookups
    │
    └── clients/
        ├── admin/                ← admin tenant data
        │   ├── company_state.json
        │   └── searches/
        │       └── *.csv
        ├── brj/                  ← cliente BRJ
        │   ├── company_state.json
        │   └── searches/
        └── <otro_tenant>/        ← cliente futuro

Usage:
    from lib.paths import get_current_tenant, get_tenant_state_file, get_tenant_searches_dir

    tenant = get_current_tenant()  # lee de st.session_state
    state_path = get_tenant_state_file(tenant)
    searches_dir = get_tenant_searches_dir(tenant)
"""
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SCRIPT_DIR / "data"
CLIENTS_DIR = DATA_DIR / "clients"
SHARED_DIR = DATA_DIR / "_shared"


def get_current_tenant(default: str = "default") -> str:
    """Devuelve el tenant del session_state actual. Fallback: default."""
    try:
        import streamlit as st
        tenant = st.session_state.get("tenant")
        if tenant:
            return tenant
    except Exception:
        pass
    return default


def get_current_tier(default: str = "starter") -> str:
    """Devuelve el tier del usuario actual. Fallback: starter."""
    try:
        import streamlit as st
        tier = st.session_state.get("tier")
        if tier:
            return tier
    except Exception:
        pass
    return default


def get_tenant_data_dir(tenant: str) -> Path:
    """data/clients/<tenant>/ — crea si no existe."""
    p = CLIENTS_DIR / tenant
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_tenant_state_file(tenant: str) -> Path:
    """data/clients/<tenant>/company_state.json"""
    return get_tenant_data_dir(tenant) / "company_state.json"


def get_tenant_searches_dir(tenant: str) -> Path:
    """data/clients/<tenant>/searches/ — crea si no existe."""
    p = get_tenant_data_dir(tenant) / "searches"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_tenant_usage_file(tenant: str) -> Path:
    """data/clients/<tenant>/usage.json — credit tracking per month."""
    return get_tenant_data_dir(tenant) / "usage.json"


def get_shared_cache_file(name: str) -> Path:
    """data/_shared/<name> — compartido entre tenants."""
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    return SHARED_DIR / name
