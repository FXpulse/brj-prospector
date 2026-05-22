"""
tiers.py - Configuración de tiers de SCM Prospector.

Tier limits son hardcoded acá por ahora (Phase 1). Move a config.json si
en el futuro queremos cambiarlos sin redeploy.

Cada tier define:
- monthly_emails: max email lookups (Hunter o Apollo) por mes
- monthly_phones: max phone lookups por mes
- max_users: max users por tenant
- price_usd: precio mensual (informativo, no se usa para enforcement)
"""

TIERS = {
    "starter": {
        "label": "Starter",
        "monthly_emails": 300,
        "monthly_phones": 30,
        "max_users": 1,
        "price_usd": 147,
        "color": "#64748B",  # slate
    },
    "pro": {
        "label": "Pro",
        "monthly_emails": 1000,
        "monthly_phones": 100,
        "max_users": 3,
        "price_usd": 297,
        "color": "#10B981",  # emerald (sweet spot)
    },
    "custom": {
        "label": "Custom",
        "monthly_emails": 999_999,
        "monthly_phones": 999_999,
        "max_users": 999,
        "price_usd": 497,
        "color": "#7C3AED",  # purple
    },
    "admin": {
        "label": "Admin",
        "monthly_emails": 999_999,
        "monthly_phones": 999_999,
        "max_users": 999,
        "price_usd": 0,
        "color": "#0F172A",  # charcoal
    },
}


def get_tier_config(tier: str) -> dict:
    """Devuelve config del tier. Fallback a starter si tier no existe."""
    return TIERS.get(tier, TIERS["starter"])


def get_tier_limit(tier: str, resource: str) -> int:
    """resource: 'emails' o 'phones'. Devuelve el límite mensual."""
    cfg = get_tier_config(tier)
    if resource == "emails":
        return cfg["monthly_emails"]
    if resource == "phones":
        return cfg["monthly_phones"]
    return 0


def is_unlimited(tier: str) -> bool:
    """Custom y admin son efectivamente unlimited."""
    return tier in ("custom", "admin")
