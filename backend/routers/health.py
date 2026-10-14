import logging

from fastapi import APIRouter
from pymongo.errors import OperationFailure, PyMongoError, ServerSelectionTimeoutError

from config import get_settings
from database import get_client

router = APIRouter(prefix="/api", tags=["health"])
log = logging.getLogger("sales.health")


@router.get("/health")
def health():
    settings = get_settings()
    db = {"connected": False, "database": settings.database_name,
          "collection": settings.collection_name, "collectionExists": False, "error": None}
    try:
        client = get_client()
        client.admin.command("ping")
        db["connected"] = True
        names = client[settings.database_name].list_collection_names()
        db["collectionExists"] = settings.collection_name in names
        if not db["collectionExists"]:
            db["error"] = "Database or collection not found."
    except RuntimeError as exc:  # missing/placeholder URI (message contains no secrets)
        db["error"] = str(exc)
    except ServerSelectionTimeoutError:
        db["error"] = "Timed out: check Atlas Network Access (IP allow-list) and that the cluster is running."
    except OperationFailure:
        db["error"] = "Authentication failed or the database user lacks permission."
    except PyMongoError as exc:
        db["error"] = f"Database error ({type(exc).__name__})."
    if db["error"]:
        log.warning("health check: %s", db["error"])
    ok = db["connected"] and db["collectionExists"]
    return {"status": "ok" if ok else "degraded", "database": db}
