"""Load the Meridian demo tenant, users, documents, and included agent lease."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from . import auth, config, db


def _uid(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex[:12]


def load_seed() -> dict:
    path = Path(config.SEED_PATH)
    if not path.exists():
        return {"company": {"name": "Demo GmbH"}, "docs": [], "agents": []}
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_seeded(conn=None) -> dict:
    """Idempotent: creates the demo org once, then no-ops."""
    c = conn or db.get_conn()
    db.init_db(c)
    seed = load_seed()
    company = seed.get("company") or {}
    name = company.get("name") or "Meridian Industrie GmbH"
    existing = c.execute("SELECT id FROM orgs WHERE slug = ?", ("meridian",)).fetchone()
    if existing:
        return {"org_id": existing["id"], "created": False}

    org_id = "org-meridian"
    now = db.now_iso()
    with db.tx(c):
        c.execute(
            "INSERT INTO orgs (id, name, slug, tagline, created_at) VALUES (?, ?, ?, ?, ?)",
            (org_id, name, "meridian", company.get("tagline") or "", now),
        )
        c.execute(
            """INSERT INTO users (id, org_id, email, name, password_hash, role, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "user-cfo",
                org_id,
                config.DEMO_EMAIL.lower(),
                config.DEMO_NAME,
                auth.hash_password(config.DEMO_PASSWORD),
                config.DEMO_ROLE,
                now,
            ),
        )
        people = company.get("people") or {}
        c.execute(
            """INSERT INTO users (id, org_id, email, name, password_hash, role, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "user-ceo",
                org_id,
                "markus.brandt@meridian.example",
                people.get("ceo") or "Markus Brandt",
                auth.hash_password(config.DEMO_PASSWORD),
                "board",
                now,
            ),
        )
        for doc in seed.get("docs") or []:
            insert_document(c, org_id, doc)
        c.execute(
            """INSERT INTO leases (id, org_id, agent_id, status, since, included)
               VALUES (?, ?, ?, 'active', 'inklusive', 1)""",
            (_uid("lease"), org_id, "auskunft"),
        )
        db.audit(org_id, "system", "seed", "Demo-Mandant Meridian angelegt", conn=c)
    return {"org_id": org_id, "created": True}


def insert_document(conn, org_id: str, doc: dict) -> None:
    body_parts = doc.get("body_parts") or []
    body = doc.get("body") or ""
    if body_parts and not body:
        body = "\n".join(p.get("t") if isinstance(p, dict) else str(p) for p in body_parts)
    extra = {
        k: doc[k]
        for k in ("lineItems", "from", "to", "cc", "subject", "attachments", "quoted")
        if doc.get(k)
    }
    conn.execute(
        """INSERT INTO documents (
            id, org_id, title, type, module, path, author, date, snippet, body,
            body_json, locked, locked_role, classification, extra_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            doc["id"],
            org_id,
            doc.get("title") or doc["id"],
            doc.get("type") or "",
            doc.get("module") or "wissen",
            doc.get("path") or "",
            doc.get("author") or "",
            doc.get("date") or "",
            doc.get("snippet") or "",
            body,
            json.dumps(body_parts, ensure_ascii=False),
            1 if doc.get("locked") else 0,
            doc.get("lockedRole"),
            doc.get("classification"),
            json.dumps(extra, ensure_ascii=False),
        ),
    )
    row = conn.execute("SELECT rowid FROM documents WHERE id = ?", (doc["id"],)).fetchone()
    conn.execute(
        "INSERT INTO documents_fts (rowid, title, snippet, body, author, type) VALUES (?, ?, ?, ?, ?, ?)",
        (
            row["rowid"],
            doc.get("title") or "",
            doc.get("snippet") or "",
            body,
            doc.get("author") or "",
            doc.get("type") or "",
        ),
    )
