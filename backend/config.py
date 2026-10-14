"""Application settings, read once from backend/.env (never logged or returned by the API)."""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    database_name: str
    collection_name: str
    suppliers_collection: str
    low_stock_threshold: int
    cors_origins: tuple[str, ...]
    api_key: str


@lru_cache
def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return Settings(
        mongodb_uri=os.getenv("MONGODB_URI", ""),
        database_name=os.getenv("DATABASE_NAME", ""),
        collection_name=os.getenv("COLLECTION_NAME", ""),
        suppliers_collection=os.getenv("SUPPLIERS_COLLECTION", "suppliers"),
        low_stock_threshold=int(os.getenv("LOW_STOCK_THRESHOLD", "10")),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        api_key=os.getenv("API_KEY", ""),
    )
