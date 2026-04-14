"""Wipe DB + Storage and insert 3 demo clients for the Ledgerly demo."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import get_supabase

DEMO_CLIENTS = [
    {"code": "DUPONT", "name": "Cabinet Dupont Immobilier"},
    {"code": "MARTIN", "name": "Martin Conseil SARL"},
    {"code": "LEROY", "name": "Leroy Batiment SAS"},
]

BUCKET = "invoices"


def wipe_storage(sb):
    """Remove all files from the invoices bucket."""
    try:
        sb.storage.get_bucket(BUCKET)
    except Exception:
        print(f"  Bucket '{BUCKET}' does not exist, skipping storage wipe.")
        return

    # List and remove all files recursively
    for prefix in ["_inbox", ""]:
        try:
            files = sb.storage.from_(BUCKET).list(prefix)
            if not files:
                continue
            paths = []
            for f in files:
                name = f.get("name", "")
                if not name or f.get("id") is None:
                    # It's a folder — list its contents
                    folder = f"{prefix}/{name}" if prefix else name
                    try:
                        sub = sb.storage.from_(BUCKET).list(folder)
                        for sf in sub:
                            if sf.get("id") is not None:
                                paths.append(f"{folder}/{sf['name']}")
                    except Exception:
                        pass
                else:
                    full = f"{prefix}/{name}" if prefix else name
                    paths.append(full)
            if paths:
                sb.storage.from_(BUCKET).remove(paths)
                print(f"  Removed {len(paths)} file(s) from '{prefix or '/'}'")
        except Exception as e:
            print(f"  Warning listing '{prefix}': {e}")


def wipe_db(sb):
    """Delete all invoices, suppliers, then clients."""
    for table in ["invoices", "suppliers", "clients"]:
        try:
            sb.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            print(f"  Wiped table: {table}")
        except Exception as e:
            print(f"  Warning wiping {table}: {e}")


def seed_clients(sb):
    """Insert demo clients."""
    for client in DEMO_CLIENTS:
        sb.table("clients").insert(client).execute()
        print(f"  Inserted client: {client['code']} — {client['name']}")


def run():
    print("Seed demo: connecting to Supabase...")
    sb = get_supabase()

    print("Wiping storage...")
    wipe_storage(sb)

    print("Wiping database...")
    wipe_db(sb)

    print("Seeding clients...")
    seed_clients(sb)

    print("Done.")


if __name__ == "__main__":
    run()
