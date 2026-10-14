"""Write-access guard. Writes require the X-API-Key header to match API_KEY from .env."""
import hmac

from fastapi import Header, HTTPException

from config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = get_settings().api_key
    if not expected or expected == "change_me":
        raise HTTPException(503, "Write operations are disabled: API_KEY is not configured on the server.")
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(401, "Missing or invalid API key.")
