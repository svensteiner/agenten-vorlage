"""Serve the product API and the prototype UI from one process."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from product.api import router
from product.config import HOST, PORT
from product.db import connect
from product.seed import ensure_seeded

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "prototype"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    conn = connect()
    try:
        ensure_seeded(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="AI Studio", version="0.9.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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

    uvicorn.run("product.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    run()
