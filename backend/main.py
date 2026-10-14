import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import (AutoReconnect, DuplicateKeyError, ExecutionTimeout,
                            OperationFailure, PyMongoError)

from config import get_settings
from routers import health, sales
from services.sales_service import InvalidQuery, SaleNotFound

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("sales")

app = FastAPI(title="Sales API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)
app.include_router(health.router)
app.include_router(sales.router)


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message})


@app.exception_handler(SaleNotFound)
async def _not_found(_: Request, __: SaleNotFound):
    return _error(404, "Sale not found.")


@app.exception_handler(InvalidQuery)
async def _invalid(_: Request, exc: InvalidQuery):
    return _error(400, str(exc))


@app.exception_handler(DuplicateKeyError)
async def _dup_key(_: Request, __: DuplicateKeyError):
    return _error(409, "Conflict: a record with this identifier already exists.")


@app.exception_handler(AutoReconnect)  # includes server-selection and network timeouts
async def _unavailable(_: Request, exc: AutoReconnect):
    log.warning("database unavailable: %s", type(exc).__name__)
    return _error(503, "Database unavailable. Check the connection and Atlas Network Access, then retry.")


@app.exception_handler(ExecutionTimeout)
async def _timeout(_: Request, __: ExecutionTimeout):
    return _error(504, "The database took too long to respond.")


@app.exception_handler(OperationFailure)
async def _op_failure(_: Request, exc: OperationFailure):
    log.warning("database operation failed: code=%s", exc.code)
    if exc.code in (13, 18):
        return _error(403, "The database user lacks permission for this operation.")
    return _error(500, "Database operation failed.")


@app.exception_handler(PyMongoError)
async def _mongo(_: Request, exc: PyMongoError):
    log.warning("database error: %s", type(exc).__name__)
    return _error(503, "Database error. Please retry.")


@app.exception_handler(RuntimeError)
async def _config(_: Request, exc: RuntimeError):
    log.error("configuration error: %s", exc)
    return _error(503, "Server is not configured to reach the database.")
