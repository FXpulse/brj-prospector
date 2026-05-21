"""
config_loader.py - Single source of truth para cargar config.

Prioridad:
1. st.secrets (Streamlit Cloud production)
2. config.json local (development)
3. {} vacío (raise error en el caller)
"""
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = SCRIPT_DIR / "config.json"


def _to_plain_dict(obj):
    """Convert nested AttrDict (st.secrets) → plain dict + list.

    Streamlit secrets son AttrDict que se comporta como dict pero no es serializable.
    """
    if obj is None:
        return None
    if hasattr(obj, "items") and not isinstance(obj, (str, bytes)):
        return {k: _to_plain_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain_dict(v) for v in obj]
    # Strings, ints, floats, bools, etc. — return as is
    return obj


def load_config():
    """Devuelve el config dict. Prioriza st.secrets > config.json > {}."""

    # Strategy 1: Streamlit secrets (production)
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            try:
                # st.secrets puede ser empty si no hay secrets configurados
                # Convertir todo a plain dict para downstream compat
                secrets = _to_plain_dict(st.secrets)
                if secrets and any(k for k in secrets.keys() if not k.startswith("_")):
                    return secrets
            except Exception:
                pass
    except ImportError:
        # streamlit no instalado (modo CLI / test)
        pass

    # Strategy 2: local config.json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Error leyendo {CONFIG_FILE}: {e}")

    # Strategy 3: empty config — caller decide qué hacer
    return {}


def has_config():
    """True si hay config cargable de cualquier fuente."""
    cfg = load_config()
    return bool(cfg) and "ghl" in cfg
