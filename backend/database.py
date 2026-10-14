"""MongoDB connection. The client is created lazily so the API can start (and report
a clear health status) even when the database is unreachable."""
from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection

from config import get_settings


@lru_cache
def get_client() -> MongoClient:
    settings = get_settings()
    if not settings.mongodb_uri or settings.mongodb_uri.startswith("your_"):
        raise RuntimeError("MONGODB_URI is not configured in backend/.env")
    return MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        socketTimeoutMS=10000,
    )


def get_sales_collection() -> Collection:
    settings = get_settings()
    return get_client()[settings.database_name][settings.collection_name]
