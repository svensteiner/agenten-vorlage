"""Serve the product API and the prototype UI from one process."""

from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
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
            created = tenancy.bootstrap_if_empty(conn)
            leftover = created or config.has_bootstrap_residue()
            if leftover:
                if config.consume_bootstrap_env():
                    logging.getLogger("product").info(
                        "Bootstrap-Zugang aus der Datendatei entfernt."
                    )
                else:
                    logging.getLogger("product").info(
                        "Bootstrap-Zugang aus der Prozessumgebung entfernt."
                    )
        except ValueError as exc:
            raise RuntimeError("Bootstrap fehlgeschlagen: %s" % exc) from exc
        conn.commit()
        if config.is_production() and config.allow_demo_seed():
            logging.getLogger("product").warning(
                "Produktion läuft mit Demo-Seed. AISTUDIO_ALLOW_DEMO_SEED=false setzen."
            )
    finally:
        conn.close()
    from product import housekeeping

    try:
        housekeeping.run_once()
    except Exception:
        logging.getLogger("product.housekeeping").exception("housekeeping skipped")
    housekeeping.start_loop()
    config.write_pid_file()
    yield
    housekeeping.stop_loop()
    config.clear_pid_file()


app = FastAPI(
    title="AI Studio",
    version=config.VERSION,
    lifespan=lifespan,
    **config.docs_kwargs(),
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
_hosts = config.allowed_hosts()
if _hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_hosts)
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


_STATIC_EXT = {".js", ".css", ".html", ".svg", ".png", ".ico", ".woff", ".woff2", ".map"}
_STATIC_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


@app.get("/")
def index():
    return FileResponse(PROTO / "index.html")


@app.get("/{path:path}")
def static_file(path: str):
    if path.startswith("api/") or path == "api":
        raise HTTPException(404, "Not found")
    if (
        ".." in path
        or path.startswith(".")
        or not _STATIC_NAME.match(path)
        or any(part.startswith(".") for part in path.split("/"))
        or Path(path).suffix.lower() not in _STATIC_EXT
    ):
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
        forwarded_allow_ips=config.uvicorn_forwarded_allow_ips(),
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    run()
