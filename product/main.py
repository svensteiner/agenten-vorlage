"""Serve the product API and the prototype UI from one process."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from product import config
from product.api import router
from product.db import connect
from product.security import AccessLogMiddleware, LimitRequestMiddleware, SecurityHeadersMiddleware
from product.seed import ensure_seeded

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "prototype"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config.validate_runtime()
    conn = connect()
    try:
        ensure_seeded(conn)
        from product import tenancy

        try:
            tenancy.bootstrap_if_empty(conn)
        except ValueError as exc:
            raise RuntimeError("Bootstrap fehlgeschlagen: %s" % exc) from exc
        conn.commit()
    finally:
        conn.close()
    from product.housekeeping import prune

    try:
        prune()
    except Exception:
        logging.getLogger("product.housekeeping").exception("housekeeping skipped")
    yield


_docs = None if config.is_production() else "/docs"
app = FastAPI(
    title="AI Studio",
    version=config.VERSION,
    lifespan=lifespan,
    docs_url=_docs,
    redoc_url=None if config.is_production() else "/redoc",
)
origins = config.cors_origins()
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LimitRequestMiddleware)
app.add_middleware(AccessLogMiddleware)
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
app.include_router(router, prefix="/api")


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "") or request.headers.get("x-request-id") or "-")


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    rid = _request_id(request)
    if config.is_production():
        return JSONResponse({"detail": "Anfrage ungültig.", "request_id": rid}, status_code=422)
    return JSONResponse({"detail": exc.errors(), "request_id": rid}, status_code=422)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(
        {"detail": exc.detail, "request_id": _request_id(request)},
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    rid = _request_id(request)
    logging.getLogger("product").exception("unhandled rid=%s", rid)
    detail = (
        str(exc)
        if not config.is_production()
        else "Interner Fehler. Bitte später erneut versuchen."
    )
    return JSONResponse({"detail": detail, "request_id": rid}, status_code=500)


@app.get("/")
def index():
    return FileResponse(PROTO / "index.html")


@app.get("/{path:path}")
def static_file(path: str):
    if path.startswith("api/") or path == "api":
        raise HTTPException(404, "Not found")
    dest = (PROTO / path).resolve()
    try:
        dest.relative_to(PROTO.resolve())
    except ValueError as exc:
        raise HTTPException(404, "Not found") from exc
    if dest.is_file():
        return FileResponse(dest)
    raise HTTPException(404, "Not found")


def run() -> None:
    import uvicorn

    config.validate_runtime()
    uvicorn.run(
        "product.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        access_log=False,
        proxy_headers=config.trust_proxy(),
        forwarded_allow_ips="*" if config.trust_proxy() else None,
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    run()
