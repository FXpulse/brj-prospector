"""
migrate_legacy_to_tenant.py - Mueve data legacy (single-tenant) a un tenant folder.

Antes de multi-tenant, los datos vivían en:
    data/company_state.json
    data/searches/*.csv

Después, viven en:
    data/clients/<tenant>/company_state.json
    data/clients/<tenant>/searches/*.csv

Uso:
    python scripts/migrate_legacy_to_tenant.py <tenant_slug>
    python scripts/migrate_legacy_to_tenant.py brj
    python scripts/migrate_legacy_to_tenant.py brj --dry-run

Hace MOVE (no copy). Si querés mantener backup, hacelo manual primero.

Para BRJ (los datos actuales que llevan trabajo de los recruiters):
    python scripts/migrate_legacy_to_tenant.py brj
"""
import argparse
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SCRIPT_DIR / "data"
LEGACY_STATE = DATA_DIR / "company_state.json"
LEGACY_SEARCHES = DATA_DIR / "searches"


def main():
    parser = argparse.ArgumentParser(description="Migra data legacy a tenant folder")
    parser.add_argument("tenant", help="Slug del tenant destino (ej: brj)")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar qué haría sin tocar archivos")
    args = parser.parse_args()

    tenant = args.tenant.strip().lower()
    if not tenant or "/" in tenant or "\\" in tenant:
        print(f"ERROR: tenant slug inválido: '{tenant}'", file=sys.stderr)
        sys.exit(1)

    tenant_dir = DATA_DIR / "clients" / tenant
    tenant_state = tenant_dir / "company_state.json"
    tenant_searches = tenant_dir / "searches"

    print("=" * 60)
    print(f"Migrando legacy data → tenant '{tenant}'")
    print("=" * 60)
    print(f"  Source state:    {LEGACY_STATE}")
    print(f"  Source searches: {LEGACY_SEARCHES}")
    print(f"  Dest dir:        {tenant_dir}")
    print(f"  Dry run:         {args.dry_run}")
    print()

    actions = []

    # 1. State file
    if LEGACY_STATE.exists():
        if tenant_state.exists():
            actions.append(("WARN", f"Destino YA EXISTE: {tenant_state}. Skipping. Renombrá/borrá el destino primero si querés sobrescribir."))
        else:
            actions.append(("MOVE", f"{LEGACY_STATE} → {tenant_state}"))
    else:
        actions.append(("SKIP", "No legacy state file."))

    # 2. Searches CSVs
    if LEGACY_SEARCHES.exists() and LEGACY_SEARCHES.is_dir():
        csvs = list(LEGACY_SEARCHES.glob("*.csv"))
        if csvs:
            for csv in csvs:
                dest = tenant_searches / csv.name
                if dest.exists():
                    actions.append(("WARN", f"Destino YA EXISTE: {dest}. Skipping {csv.name}."))
                else:
                    actions.append(("MOVE", f"{csv} → {dest}"))
        else:
            actions.append(("SKIP", "No legacy CSVs en searches/."))
    else:
        actions.append(("SKIP", "No legacy searches/ folder."))

    # Print plan
    for verb, msg in actions:
        print(f"  [{verb}] {msg}")
    print()

    if args.dry_run:
        print("Dry-run terminado — nada cambiado.")
        return

    # Execute
    confirm = input(f"Confirmás migración a tenant '{tenant}'? (yes/no): ").strip().lower()
    if confirm not in ("yes", "y", "si", "sí"):
        print("Cancelado.")
        return

    tenant_dir.mkdir(parents=True, exist_ok=True)
    tenant_searches.mkdir(parents=True, exist_ok=True)

    moved = 0
    skipped = 0
    for verb, msg in actions:
        if verb != "MOVE":
            skipped += 1
            continue
        # Parse src → dest from msg
        parts = msg.split(" → ")
        src = Path(parts[0])
        dest = Path(parts[1])
        try:
            shutil.move(str(src), str(dest))
            print(f"  ✓ moved {src.name}")
            moved += 1
        except Exception as e:
            print(f"  ✗ ERROR moving {src}: {e}", file=sys.stderr)

    print()
    print(f"Migración terminada: {moved} archivos movidos, {skipped} skipped.")
    print(f"Los datos del tenant '{tenant}' ahora viven en: {tenant_dir}")
    print()
    print("Siguiente paso:")
    print(f"  1. Crear user(s) para tenant '{tenant}' en config.json bajo auth.users")
    print(f"  2. Cuando esos users logueen, verán esta data automáticamente")


if __name__ == "__main__":
    main()
