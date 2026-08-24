"""Permission-faithful full-text retrieval over the tenant document store."""

from __future__ import annotations

import re
from typing import Any

from . import db

_FTS_KEEP = re.compile(r"[A-Za-zÄÖÜäöüß0-9\-]{2,}")


def fts_query(text: str) -> str:
    tokens = _FTS_KEEP.findall(text or "")
    if not tokens:
        return ""
    # Phrase-OR of quoted tokens; FTS5 special chars stripped by the regex.
    return " OR ".join('"%s"' % t.replace('"', "") for t in tokens[:12])


def can_read(doc: dict, role: str) -> bool:
    if not doc.get("locked"):
        return True
    return role in {"board", "admin"}


def _hydrate(row) -> dict[str, Any]:
    item = db.row_dict(row)
    assert item is not None
    item["body_parts"] = db.parse_json(item.get("body_json"), [])
    item["extra"] = db.parse_json(item.get("extra_json"), {})
    item["locked"] = bool(item.get("locked"))
    return item


def retrieve(
    org_id: str,
    query: str,
    *,
    role: str = "member",
    limit: int = 8,
    conn=None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (visible_hits, withheld_locked_hits) for a query."""
    c = conn or db.get_conn()
    match = fts_query(query)
    rows: list[Any]
    if match:
        rows = c.execute(
            """
            SELECT d.*, bm25(documents_fts) AS rank
            FROM documents_fts
            JOIN documents d ON d.rowid = documents_fts.rowid
            WHERE d.org_id = ? AND documents_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (org_id, match, limit * 3),
        ).fetchall()
    else:
        rows = []
    if not rows:
        like = "%" + (query or "").strip()[:80] + "%"
        rows = c.execute(
            """
            SELECT d.*, 0 AS rank FROM documents d
            WHERE d.org_id = ? AND (
                d.title LIKE ? OR d.snippet LIKE ? OR d.body LIKE ? OR d.author LIKE ?
            )
            LIMIT ?
            """,
            (org_id, like, like, like, like, limit * 3),
        ).fetchall()

    visible: list[dict[str, Any]] = []
    withheld: list[dict[str, Any]] = []
    for row in rows:
        item = _hydrate(row)
        if can_read(item, role):
            visible.append(item)
            if len(visible) >= limit:
                # Keep scanning a little for withheld signals on later rows.
                if len(visible) + len(withheld) >= limit * 2:
                    break
        else:
            withheld.append(
                {
                    "docId": item["id"],
                    "title": item["title"],
                    "classification": item.get("classification") or "Vertraulich",
                    "lockedRole": item.get("locked_role") or "Vorstand",
                }
            )
    visible = visible[:limit]
    return visible, withheld


def search(
    org_id: str,
    query: str,
    *,
    role: str = "member",
    limit: int = 8,
    conn=None,
) -> list[dict[str, Any]]:
    visible, withheld = retrieve(org_id, query, role=role, limit=limit, conn=conn)
    for item in visible:
        item["_withheld"] = withheld
    return visible


def get_document(org_id: str, doc_id: str, role: str, conn=None) -> dict[str, Any] | None:
    c = conn or db.get_conn()
    row = c.execute(
        "SELECT * FROM documents WHERE org_id = ? AND id = ?", (org_id, doc_id)
    ).fetchone()
    item = db.row_dict(row)
    if not item:
        return None
    item["body_parts"] = db.parse_json(item.get("body_json"), [])
    item["extra"] = db.parse_json(item.get("extra_json"), {})
    if not can_read(item, role):
        item["body"] = ""
        item["body_parts"] = []
        item["denied"] = True
    return item


def list_documents(org_id: str, role: str, conn=None) -> list[dict[str, Any]]:
    c = conn or db.get_conn()
    rows = c.execute(
        "SELECT * FROM documents WHERE org_id = ? ORDER BY date DESC, title", (org_id,)
    ).fetchall()
    out = []
    for row in rows:
        item = _hydrate(row)
        if not can_read(item, role):
            item["body"] = ""
            item["body_parts"] = []
            item["denied"] = True
        out.append(item)
    return out


def to_frontend_doc(item: dict[str, Any]) -> dict[str, Any]:
    """Shape a stored document the way prototype/app.js expects in DOCS."""
    extra = item.get("extra") if isinstance(item.get("extra"), dict) else db.parse_json(item.get("extra_json"), {})
    out = {
        "id": item["id"],
        "title": item.get("title") or item["id"],
        "type": item.get("type") or "",
        "module": item.get("module") or "wissen",
        "path": item.get("path") or "",
        "author": item.get("author") or "",
        "date": item.get("date") or "",
        "snippet": item.get("snippet") or "",
        "body_parts": item.get("body_parts") or [],
        "locked": bool(item.get("locked")),
        "lockedRole": item.get("locked_role") or item.get("lockedRole"),
        "classification": item.get("classification"),
        "denied": bool(item.get("denied")),
    }
    if extra:
        out.update(extra)
    return out


def withheld_payload(withheld: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not withheld:
        return None
    return {
        "count": len(withheld),
        "role": withheld[0].get("lockedRole") or "Vorstand",
        "note": (
            "AI Studio respektiert die bestehenden Berechtigungen Ihres Kontos. "
            "Diese Dokumente werden Ihnen nicht angezeigt und flossen nicht in die Antwort ein."
        ),
        "docs": [w["docId"] for w in withheld],
    }


def sources_from(hits: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    return [
        {
            "docId": h["id"],
            "relevance": relevance(h.get("rank"), i),
            "quote": quote_from(h, query),
        }
        for i, h in enumerate(hits)
    ]


def extractive_text(hits: list[dict[str, Any]], query: str) -> str:
    from html import escape

    if not hits:
        return (
            "Ich konnte zu dieser Frage keine passenden Dokumente in Ihrer "
            "Wissensbasis finden."
        )
    parts = [
        f"Ich habe <b>{len(hits)} relevante Dokument(e)</b> in Ihrer privaten "
        f"Wissensbasis gefunden."
    ]
    for h in hits[:4]:
        title = escape(h.get("title") or h["id"])
        snippet = escape(quote_from(h, query, 220))
        parts.append(f"<p><b>{title}</b> — {snippet}</p>")
    return "".join(parts)


def ask(org_id: str, query: str, *, role: str = "member", conn=None) -> dict[str, Any]:
    """Permission-faithful answer in the prototype answer-card shape."""
    hits, withheld = retrieve(org_id, query, role=role, limit=5, conn=conn)
    withheld_ui = withheld_payload(withheld)
    sources = sources_from(hits, query)
    reasoning = [
        "Frage entgegengenommen.",
        "Volltextsuche über die Mandanten-Wissensbasis (FTS5).",
        "Zugriffsrechte des Kontos geprüft — fail-closed.",
    ]
    if withheld:
        reasoning.append(
            f"{len(withheld)} Treffer als „{withheld_ui['role']}“ klassifiziert — Inhalt nicht gelesen."
        )

    text = ""
    via = "extractive"
    if hits:
        text = _maybe_llm_answer(query, hits) or extractive_text(hits, query)
        via = "llm" if text and not text.startswith("Ich habe <b>") else "extractive"
        if via == "extractive":
            reasoning.append("Antwort extractiv aus den Treffern formuliert (kein Modell konfiguriert oder Fallback).")
        else:
            reasoning.append("Antwort mit dem konfigurierten Sprachmodell formuliert, nur aus den Treffern.")
        confidence = min(94, 70 + len(hits) * 6)
    elif withheld_ui:
        text = (
            "Zu Ihrer Frage sind ausschließlich Dokumente vorhanden, die "
            "<b>für Sie nicht freigegeben</b> sind — siehe unten. AI Studio zeigt deren Inhalt nicht an."
        )
        reasoning.append("Ehrliche Rückmeldung statt Halluzination (fail-closed).")
        confidence = 38
    else:
        text = (
            "Ich konnte zu dieser Frage keine passenden Dokumente in der Wissensbasis finden. "
            "Formulieren Sie die Frage mit Begriffen aus Verträgen, Berichten oder Belegen."
        )
        reasoning.append("Kein ausreichend relevanter Treffer — keine Erfindung.")
        confidence = 30

    return {
        "text": text,
        "reasoning": reasoning,
        "sources": sources,
        "confidence": confidence,
        "withheld": withheld_ui,
        "related": [h["id"] for h in hits[:4]],
        "followups": _followups(query),
        "via": via,
    }


def _followups(query: str) -> list[str]:
    # Stable, useful next questions — not hallucinated document claims.
    return [
        "Warum sind die Materialkosten gestiegen?",
        "Finde alle Verträge mit automatischer Verlängerung.",
        "Erstelle eine Zusammenfassung für den Vorstand.",
    ]


def _maybe_llm_answer(query: str, hits: list[dict[str, Any]]) -> str:
    try:
        import brain
    except Exception:
        return ""
    evidence = []
    for h in hits[:4]:
        evidence.append(
            f"[{h.get('title')}] ({h.get('path')})\n{quote_from(h, query, 400)}"
        )
    system = (
        "Du bist der Auskunfts-Agent von AI Studio. Antworte auf Deutsch, knapp und belegt. "
        "Verwende nur die gelieferten Auszüge. Keine Erfindung. HTML erlaubt: <b>, <p>, <ul>, <li>."
    )
    user = f"Frage: {query}\n\nAuszüge:\n\n" + "\n\n".join(evidence)
    try:
        text = brain.complete(system, user, temperature=0.2, max_tokens=700, use_fast=True)
    except Exception:
        return ""
    return (text or "").strip()


def quote_from(doc: dict[str, Any], query: str, n: int = 180) -> str:
    body = doc.get("body") or doc.get("snippet") or ""
    q = (query or "").lower()
    words = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{3,}", q)]
    low = body.lower()
    idx = -1
    for w in words:
        idx = low.find(w.lower())
        if idx >= 0:
            break
    if idx < 0:
        return (doc.get("snippet") or body)[:n]
    start = max(0, idx - 40)
    snippet = body[start : start + n].strip()
    if start > 0:
        snippet = "…" + snippet
    if start + n < len(body):
        snippet = snippet + "…"
    return snippet


def relevance(rank: float | None, index: int) -> int:
    if rank is None:
        return max(55, 92 - index * 8)
    # bm25: more negative is better. Map into 55–98.
    score = 98 + (rank * 4)  # rank typically -10..0
    return int(max(55, min(98, score)))
