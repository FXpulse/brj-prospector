"""
hash_password.py - Utility para generar bcrypt hashes para auth users.

Uso:
    python scripts/hash_password.py
    # Te pide la password (no se muestra) → imprime el hash listo para pegar en config

Pegá el output en config.json (local) o Streamlit Secrets (cloud) bajo
auth.users.<username>.password_hash
"""
import getpass
import sys

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt no instalado. Run: pip install bcrypt", file=sys.stderr)
    sys.exit(1)


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def main():
    print("=" * 60)
    print("SCM Prospector — Password Hash Generator")
    print("=" * 60)

    if len(sys.argv) > 1:
        # Modo argumento (NO recomendado, password queda en historial bash)
        plaintext = sys.argv[1]
    else:
        plaintext = getpass.getpass("Password (no se muestra): ")
        confirm = getpass.getpass("Confirmar password: ")
        if plaintext != confirm:
            print("ERROR: passwords no coinciden", file=sys.stderr)
            sys.exit(1)

    if len(plaintext) < 8:
        print("⚠️  Warning: password muy corto (< 8 chars). Usá uno más largo en producción.")

    hashed = hash_password(plaintext)
    print()
    print("✅ Hash generado:")
    print()
    print(hashed)
    print()
    print("Pegalo en config.json bajo:")
    print('  "auth": {')
    print('    "users": {')
    print('      "<username>": {')
    print(f'        "password_hash": "{hashed}",')
    print('        ... (name, email, tenant, tier)')
    print("      }")
    print("    }")
    print("  }")


if __name__ == "__main__":
    main()
