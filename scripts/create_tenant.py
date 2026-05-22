"""
create_tenant.py - Setup automático de cliente nuevo en SCM Prospector.

Uso:
    python scripts/create_tenant.py --email user@agency.com --name "John Doe" --tenant agency_slug --tier pro

Genera:
- Random temp password (12 chars)
- Bcrypt hash del password
- Bloque JSON/TOML listo para pegar en config.json + Streamlit Secrets
- Crea data/clients/<tenant>/ con subfolders necesarios
- Imprime email de bienvenida ready-to-copy con credenciales

NO modifica config.json directamente (vos lo pegás manualmente para safety).
NO crea el user en Streamlit Cloud (vos pegás en Secrets).
"""
import argparse
import secrets
import string
import sys
from pathlib import Path

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt no instalado. Run: pip install bcrypt", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent.parent
DATA_CLIENTS_DIR = SCRIPT_DIR / "data" / "clients"


def gen_password(length=12):
    """Random alphanumeric + 1 special char password."""
    alphabet = string.ascii_letters + string.digits
    pwd = "".join(secrets.choice(alphabet) for _ in range(length - 1))
    return pwd + secrets.choice("!@#$%")


def hash_password(plaintext):
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="Setup nuevo tenant + user para SCM Prospector")
    parser.add_argument("--email", required=True, help="Email del user (será también el username)")
    parser.add_argument("--name", required=True, help="Display name del user")
    parser.add_argument("--tenant", required=True, help="Tenant slug (ej: brj, acme_staffing)")
    parser.add_argument("--tier", default="pro", choices=["starter", "pro", "custom", "admin"], help="Tier")
    parser.add_argument("--password", default=None, help="Custom password (opcional, sino se genera random)")
    args = parser.parse_args()

    # Validate inputs
    tenant = args.tenant.strip().lower().replace(" ", "_")
    email = args.email.strip().lower()

    if "@" not in email:
        print("ERROR: email inválido", file=sys.stderr); sys.exit(1)
    if not tenant or any(c in tenant for c in "/\\"):
        print(f"ERROR: tenant slug inválido: '{tenant}'", file=sys.stderr); sys.exit(1)

    # Generate or use password
    password = args.password or gen_password()
    pwd_hash = hash_password(password)

    # Create data folder
    tenant_dir = DATA_CLIENTS_DIR / tenant
    searches_dir = tenant_dir / "searches"
    tenant_dir.mkdir(parents=True, exist_ok=True)
    searches_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"  ✅ Tenant '{tenant}' creado en: {tenant_dir}")
    print("=" * 70)
    print()
    print("📌 PEGAR EN config.json (local) bajo `auth.users`:")
    print()
    print(f'    "{email}": {{')
    print(f'      "name": "{args.name}",')
    print(f'      "email": "{email}",')
    print(f'      "password_hash": "{pwd_hash}",')
    print(f'      "tenant": "{tenant}",')
    print(f'      "tier": "{args.tier}"')
    print(f'    }},')
    print()
    print("📌 PEGAR EN Streamlit Cloud Secrets (TOML):")
    print()
    print(f'    [auth.users."{email}"]')
    print(f'    name = "{args.name}"')
    print(f'    email = "{email}"')
    print(f'    password_hash = "{pwd_hash}"')
    print(f'    tenant = "{tenant}"')
    print(f'    tier = "{args.tier}"')
    print()
    print("=" * 70)
    print(f"  🔐 TEMP PASSWORD (mandar al user en welcome email):")
    print(f"      {password}")
    print("=" * 70)
    print()
    print("📌 EMAIL DE BIENVENIDA — copia/pega y personalizá:")
    print()
    print("    Subject: Welcome to SCM Prospector — your credentials inside")
    print()
    print(f"    Hi {args.name.split()[0]},")
    print()
    print("    Welcome aboard! Your SCM Prospector account is ready.")
    print()
    print("    🔐 LOGIN")
    print(f"       URL:      https://brjprospector.streamlit.app")
    print(f"       Email:    {email}")
    print(f"       Password: {password}")
    print()
    print("    Please change this password on first login (Settings page).")
    print()
    print(f"    Your tier: {args.tier.upper()}")
    print(f"    Tenant: {tenant}")
    print()
    print("    📚 GETTING STARTED")
    print("    1. Log in with the credentials above")
    print("    2. Go to 'Companies' page")
    print("    3. Pick your industry, set Min vacancies to 5, click 🚀 Find Companies")
    print("    4. Within 5 min you'll have prospects + HR decision-maker contacts")
    print()
    print("    Questions? Reply this email or hello@theprospector.io")
    print()
    print("    — Ludmila")
    print("    Social Click Media")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
