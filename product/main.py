"""Serve the product API and the prototype UI from one process."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from product import config
from product.api import router
from product.db import connect
from product.security import SecurityHeadersMiddleware
from product.seed import ensure_seeded

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "prototype"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config.validate_runtime()
    conn = connect()
    try:
        ensure_seeded(conn)
    finally:
        conn.close()
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
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
app.include_router(router, prefix="/api")


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
    uvicorn.run("product.main:app", host=config.HOST, port=config.PORT, reload=False)


if __name__ == "__main__":
    run()
