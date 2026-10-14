"""Read-only MongoDB discovery. Lists databases, collections and sampled field names.

Never prints the URI, credentials or document values (only field names and types).
Run from backend/:  python scripts/discover.py
"""
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import (ConfigurationError, OperationFailure,
                            ServerSelectionTimeoutError)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
SKIP_DBS = {"admin", "local", "config"}
HINTS = ("inventory", "product", "stock", "item", "sku", "warehouse")


def main() -> int:
    uri = os.getenv("MONGODB_URI", "")
    if not uri or uri.startswith("your_"):
        print("FAIL: MONGODB_URI is missing or still the placeholder in backend/.env")
        return 1
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")
        print("OK: connected to MongoDB Atlas")
    except ConfigurationError:
        print("FAIL: URI is malformed or DNS lookup failed (check the mongodb+srv:// string).")
        return 1
    except ServerSelectionTimeoutError:
        print("FAIL: timeout. Likely Atlas Network Access (IP allow-list) blocks this machine, or the cluster is paused.")
        return 1
    except OperationFailure:
        print("FAIL: authentication failed or user lacks permission (check username/password and roles).")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__}")
        return 1

    try:
        dbs = [d for d in client.list_database_names() if d not in SKIP_DBS]
    except OperationFailure:
        print("FAIL: user cannot list databases. Set DATABASE_NAME in .env and re-run.")
        return 1
    only = os.getenv("DATABASE_NAME") or None
    for db_name in ([only] if only else dbs):
        try:
            cols = client[db_name].list_collection_names()
        except OperationFailure:
            print(f"- {db_name}: no permission to list collections")
            continue
        print(f"\nDatabase: {db_name} ({len(cols)} collections)")
        for col in cols:
            coll = client[db_name][col]
            try:
                count = coll.estimated_document_count()
                sample = list(coll.find().limit(5))
            except OperationFailure:
                print(f"  - {col}: no read permission")
                continue
            fields: Counter = Counter()
            for doc in sample:
                for k, v in doc.items():
                    fields[f"{k}:{type(v).__name__}"] += 1
            flag = "  <-- inventory candidate" if any(h in col.lower() for h in HINTS) else ""
            print(f"  - {col}: {count} docs{flag}")
            if fields:
                print("      fields: " + ", ".join(sorted(fields)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
