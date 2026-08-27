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


def list_documents(org_id: str, role: str, conn=None, *, limit: int = 500) -> list[dict[str, Any]]:
    c = conn or db.get_conn()
    try:
        cap = int(limit)
    except (TypeError, ValueError):
        cap = 500
    cap = max(1, min(cap, 5000))
    rows = c.execute(
        "SELECT * FROM documents WHERE org_id = ? ORDER BY date DESC, title LIMIT ?",
        (org_id, cap),
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


def ask(
    org_id: str,
    query: str,
    *,
    role: str = "member",
    conn=None,
    user_id: str | None = None,
) -> dict[str, Any]:
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
    llm_meta: dict[str, Any] = {}
    if hits:
        llm_text, llm_meta = _maybe_llm_answer(
            query, hits, org_id=org_id, user_id=user_id, conn=conn
        )
        if llm_text:
            text = llm_text
            via = "llm"
            reasoning.append(
                "Antwort über die Modell-Schicht formuliert — nur freigegebene Kurzauszüge, nicht die Wissensbasis."
            )
        else:
            text = extractive_text(hits, query)
            via = "extractive"
            if llm_meta.get("error") == "rate_limited":
                reasoning.append(
                    "Antwort extractiv auf der Instanz — Modell-Kontingent erschöpft."
                )
            elif llm_meta.get("error") == "circuit_open":
                reasoning.append(
                    "Antwort extractiv auf der Instanz — Modell vorübergehend nicht erreichbar."
                )
            else:
                reasoning.append(
                    "Antwort extractiv aus den Treffern auf der Instanz (kein Cloud-Modell oder Ausgang gesperrt)."
                )
        confidence = min(94, 70 + len(hits) * 6)
    elif withheld_ui:
        text = (
            "Zu Ihrer Frage sind ausschließlich Dokumente vorhanden, die "
            "<b>für Sie nicht freigegeben</b> sind — siehe unten. AI Studio zeigt deren Inhalt nicht an."
        )
        reasoning.append("Ehrliche Rückmeldung statt Halluzination (fail-closed).")
        confidence = 38
    else:
        store = conn or db.get_conn()
        n_docs = store.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE org_id = ?", (org_id,)
        ).fetchone()["n"]
        if n_docs == 0:
            text = (
                "Die Wissensbasis dieses Mandanten ist noch leer. "
                "Legen Sie unter Betrieb eine Textdatei ab und stellen Sie die Frage danach erneut."
            )
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
        "llm_provider": llm_meta.get("provider") or None,
        "llm_model": llm_meta.get("model") or None,
    }


def _followups(query: str) -> list[str]:
    # Stable next questions that do not assume a demo corpus.
    return [
        "Welche Dokumente liegen in der Wissensbasis?",
        "Fasse die wichtigsten Fristen und Beträge zusammen.",
        "Erstelle eine kurze Vorlage für den Vorstand.",
    ]


def _maybe_llm_answer(
    query: str,
    hits: list[dict[str, Any]],
    *,
    org_id: str | None = None,
    user_id: str | None = None,
    conn=None,
) -> tuple[str, dict[str, Any]]:
    """Formulate via the product gateway. Corpus stays local; only excerpts may leave."""
    from product import llm

    empty: dict[str, Any] = {}
    if llm.circuit_open():
        return "", {"error": "circuit_open"}
    if not llm.allow_call(org_id=org_id, user_id=user_id, conn=conn):
        return "", {"error": "rate_limited"}
    excerpts = llm.excerpts_from_hits(hits, query, quote_fn=quote_from)
    if not excerpts:
        return "", empty
    system = (
        "Du bist der Auskunfts-Agent von AI Studio. Antworte auf Deutsch, knapp und belegt. "
        "Verwende nur die gelieferten Auszüge. Keine Erfindung. HTML erlaubt: <b>, <p>, <ul>, <li>."
    )
    user = llm.build_user_prompt(query, excerpts)
    try:
        result = llm.complete(system=system, user=user)
    except Exception:
        return "", empty
    meta = {
        "provider": result.get("provider"),
        "model": result.get("model"),
        "error": result.get("error") or "",
    }
    if not result.get("ok"):
        return "", meta
    return (result.get("text") or "").strip(), meta


def quote_from(doc: dict[str, Any], query: str, n: int = 180) -> str:
    body = doc.get("body") or doc.get("snippet") or ""
    q = (query or "").lower()
    words = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{3,}", q)]
    # Longer tokens first so "Reiserichtlinie" wins over "sind".
    words = sorted(set(words), key=lambda w: (-len(w), words.index(w)))
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
