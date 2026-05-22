"""
auth.py - Wrapper de streamlit-authenticator para SCM Prospector.

Config esperado en config.json o st.secrets bajo "auth":
{
  "auth": {
    "cookie": {
      "name": "scm_prospector_auth",
      "key": "long-random-secret-for-cookie-signing",
      "expiry_days": 30
    },
    "users": {
      "<email>": {                      <-- key IS the email
        "name": "Display Name",
        "email": "user@email.com",
        "password_hash": "$2b$12$...",
        "tenant": "brj",
        "tier": "pro"
      }
    }
  }
}

Para generar password_hash: scripts/hash_password.py
"""
import streamlit as st


# ─── CSS injection helpers ──────────────────────────────────────


def _hide_sidebar_css():
    """Oculta sidebar y nav antes del login para experiencia limpia."""
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="collapsedControl"] {
                display: none !important;
            }
            section.main > div.block-container {
                max-width: 480px;
                margin: 0 auto;
                padding-top: 4rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _login_brand_block():
    """Renderiza el header de la página de login: logo + tagline."""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="
                display: inline-block;
                background: #10B981;
                color: white;
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 1.5px;
                padding: 4px 10px;
                border-radius: 999px;
                margin-bottom: 12px;
            ">BETA</div>
            <h1 style="
                color: #0F172A;
                font-size: 2rem;
                font-weight: 700;
                margin: 0;
                border: none;
                padding: 0;
            ">SCM Prospector</h1>
            <p style="color: #64748B; margin: 8px 0 0 0; font-size: 0.95rem;">
                Vacancy & Decision-Maker Intelligence for Staffing
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _login_footer():
    st.markdown(
        """
        <div style="text-align: center; margin-top: 24px; color: #94A3B8; font-size: 0.8rem;">
            Forgot your password?<br/>
            Email <a href="mailto:hello@theprospector.io" style="color: #10B981; text-decoration: none;">
            hello@theprospector.io</a> and we'll send you a new one.
        </div>
        <div style="text-align: center; margin-top: 32px; color: #CBD5E1; font-size: 0.75rem;">
            Powered by Social Click Media
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Credentials building ────────────────────────────────────────


def _build_credentials(auth_cfg):
    """Transforma auth.users → estructura que streamlit-authenticator espera.

    NOTA: la KEY de cada user en config es su email (la usamos para login).
    streamlit-authenticator también la lee como 'username' internamente.
    """
    users = auth_cfg.get("users") or {}
    return {
        "usernames": {
            email: {
                "name": data.get("name", email),
                "email": data.get("email", email),
                "password": data.get("password_hash", ""),
                # Custom fields preserved para lookup post-login
                "_tenant": data.get("tenant", "default"),
                "_tier": data.get("tier", "starter"),
            }
            for email, data in users.items()
            if data.get("password_hash")
        }
    }


def get_authenticator(auth_cfg):
    """Devuelve una instancia configurada de streamlit_authenticator.Authenticate."""
    import streamlit_authenticator as stauth

    cookie = auth_cfg.get("cookie", {})
    credentials = _build_credentials(auth_cfg)

    if not credentials["usernames"]:
        return None

    return stauth.Authenticate(
        credentials,
        cookie.get("name", "scm_prospector_auth"),
        cookie.get("key", "REPLACE_WITH_RANDOM_SECRET"),
        cookie.get("expiry_days", 30),
    )


# ─── Public API ──────────────────────────────────────────────────


def require_auth(cfg=None):
    """
    Llamá esta función al TOPE de cada page. Bloquea hasta que el user esté autenticado.

    Returns: dict con {username, email, name, tenant, tier} si autenticado.
    Stop la ejecución de la page si no autenticado.
    """
    if cfg is None:
        from lib.config_loader import load_config
        cfg = load_config()

    auth_cfg = cfg.get("auth") or {}

    if not auth_cfg.get("users"):
        st.error(
            "⚠️ Auth not configured. Add an `auth` section to config.json (local) "
            "or Streamlit Secrets (cloud) with at least one admin user. "
            "See `config.template.json` and `scripts/hash_password.py`."
        )
        st.stop()

    authenticator = get_authenticator(auth_cfg)
    if authenticator is None:
        st.error("⚠️ No valid users found in auth config (missing password_hash).")
        st.stop()

    # Detectar pre-login state para ocultar sidebar
    if not st.session_state.get("authentication_status"):
        _hide_sidebar_css()
        _login_brand_block()

    # Render login form con labels en inglés
    try:
        authenticator.login(
            location="main",
            fields={
                "Form name": "Sign in",
                "Username": "Email",
                "Password": "Password",
                "Login": "Sign in",
            },
        )
    except TypeError:
        # streamlit-authenticator versión anterior — fields kwarg no soportado
        authenticator.login(location="main")

    status = st.session_state.get("authentication_status")
    if status is False:
        st.error("❌ Email or password incorrect.")
        _login_footer()
        st.stop()
    if status is None:
        _login_footer()
        st.stop()

    # Logged in — lookup tenant + tier del config (defaults)
    email = st.session_state.get("username")  # stauth llama "username" pero es el email
    user_data = auth_cfg["users"].get(email, {})
    tenant = user_data.get("tenant", "default")
    tier = user_data.get("tier", "starter")

    # ── GHL Status verification (source of truth para billing/access) ──
    # Admin bypass: tier="admin" siempre tiene acceso (sin pago)
    if tier != "admin":
        try:
            from lib.ghl_status import verify_contact_status, is_ghl_configured
            if is_ghl_configured(cfg):
                status = verify_contact_status(email, cfg)
                if not status.get("access_granted"):
                    st.error(f"🔒 {status.get('reason', 'Account inactive')}")
                    if status.get("authenticator"):
                        pass  # let them logout if they want
                    st.stop()
                # Override tier + tenant from GHL (GHL is source of truth)
                tier = status.get("tier", tier)
                tenant = status.get("tenant", tenant)
        except Exception as e:
            # Si GHL falla, NO bloqueamos (fail-open). Logueamos.
            st.warning(f"⚠️ Status check unavailable. Contact admin if issues persist.")

    # Guardamos en session_state para acceso desde cualquier page
    st.session_state["tenant"] = tenant
    st.session_state["tier"] = tier
    st.session_state["email"] = email

    return {
        "username": email,
        "email": email,
        "name": st.session_state.get("name", email),
        "tenant": tenant,
        "tier": tier,
        "authenticator": authenticator,  # para logout button
    }


def render_user_chip(user):
    """Sidebar widget: user identity + this month's usage + logout."""
    if not user:
        return
    with st.sidebar:
        st.markdown(
            f"""
            <div style="
                padding: 10px 14px;
                background: #F8FAFC;
                border-radius: 8px;
                border-left: 3px solid #10B981;
                margin-bottom: 12px;
                font-size: 0.85rem;
            ">
                <div style="font-weight: 600; color: #0F172A;">{user['name']}</div>
                <div style="color: #64748B; font-size: 0.75rem;">
                    {user['tenant'].upper()} · {user['tier'].upper()}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── This month's usage panel ───────────────────────────
        try:
            from lib.usage import get_usage
            from lib.tiers import get_tier_config, is_unlimited
            usage = get_usage(tenant=user["tenant"])
            tier_cfg = get_tier_config(user["tier"])
            unlimited = is_unlimited(user["tier"])

            email_used = usage.get("emails", 0)
            phone_used = usage.get("phones", 0)
            search_used = usage.get("searches", 0)
            email_bonus = usage.get("bonus_emails", 0)
            phone_bonus = usage.get("bonus_phones", 0)

            email_cap = tier_cfg["monthly_emails"] + email_bonus
            phone_cap = tier_cfg["monthly_phones"] + phone_bonus

            email_limit = "∞" if unlimited else email_cap
            phone_limit = "∞" if unlimited else phone_cap

            email_pct = 0 if unlimited else min(100, int(100 * email_used / max(1, email_cap)))
            phone_pct = 0 if unlimited else min(100, int(100 * phone_used / max(1, phone_cap)))

            def _bar_color(pct):
                if unlimited or pct < 60:
                    return "#10B981"
                if pct < 90:
                    return "#F59E0B"
                return "#DC2626"

            bonus_note = ""
            if email_bonus or phone_bonus:
                bonus_note = f"<div style='font-size: 0.65rem; color: #10B981; margin-top: 4px;'>✨ Bonus credits granted: {email_bonus}em + {phone_bonus}ph</div>"

            st.markdown(
                f"""
                <div style="
                    padding: 10px 14px;
                    background: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                    margin-bottom: 12px;
                    font-size: 0.78rem;
                ">
                    <div style="color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; font-size: 0.65rem; margin-bottom: 8px;">
                        This month
                    </div>
                    <div style="display: flex; justify-content: space-between; color: #0F172A; margin-bottom: 4px;">
                        <span>📧 Emails</span><span style="font-weight: 600;">{email_used} / {email_limit}</span>
                    </div>
                    <div style="background: #F1F5F9; height: 4px; border-radius: 2px; margin-bottom: 10px; overflow: hidden;">
                        <div style="background: {_bar_color(email_pct)}; height: 100%; width: {email_pct if not unlimited else 5}%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; color: #0F172A; margin-bottom: 4px;">
                        <span>📞 Phones</span><span style="font-weight: 600;">{phone_used} / {phone_limit}</span>
                    </div>
                    <div style="background: #F1F5F9; height: 4px; border-radius: 2px; margin-bottom: 10px; overflow: hidden;">
                        <div style="background: {_bar_color(phone_pct)}; height: 100%; width: {phone_pct if not unlimited else 5}%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; color: #64748B; font-size: 0.72rem;">
                        <span>🔍 Searches</span><span>{search_used}</span>
                    </div>
                    {bonus_note}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ── Top-up CTA cuando usage >= 80% ─────────────────
            near_limit = (not unlimited) and (email_pct >= 80 or phone_pct >= 80)
            if near_limit:
                if user["tier"] == "admin":
                    cta_label = "💳 Grant credits → Admin panel"
                    cta_help = "You're admin. Use the Admin panel to grant bonus credits."
                else:
                    cta_label = "✉️ Request top-up"
                    cta_help = "Email hello@theprospector.io to request more credits this month."
                st.markdown(
                    f"""
                    <a href="mailto:hello@theprospector.io?subject=Top-up request — {user['tenant']}&body=Hi, I'd like to request additional credits for my SCM Prospector account ({user['tenant']}, {user['tier']} tier). Please advise on top-up options."
                       style="
                           display: block;
                           text-align: center;
                           background: #FEF3C7;
                           border: 1px solid #F59E0B;
                           color: #92400E;
                           padding: 8px 12px;
                           border-radius: 6px;
                           text-decoration: none;
                           font-size: 0.78rem;
                           font-weight: 600;
                           margin-bottom: 12px;
                       ">
                        {cta_label}
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
        except Exception:
            pass  # silent fail if usage module not available

        if user.get("authenticator"):
            try:
                user["authenticator"].logout(
                    button_name="Sign out",
                    location="sidebar",
                )
            except TypeError:
                user["authenticator"].logout("Sign out", "sidebar")
