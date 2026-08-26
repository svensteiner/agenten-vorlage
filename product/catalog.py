"""Agent catalog (from seed) and lease/billing helpers."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from . import db
from .seed import load_seed


def catalog() -> list[dict[str, Any]]:
    return list(load_seed().get("agents") or [])


def by_id(agent_id: str) -> dict[str, Any] | None:
    for agent in catalog():
        if agent.get("id") == agent_id:
            return agent
    return None


def fleet(org_id: str, conn=None) -> list[dict[str, Any]]:
    c = conn or db.get_conn()
    rows = c.execute(
        "SELECT * FROM leases WHERE org_id = ? AND status != 'cancelled'", (org_id,)
    ).fetchall()
    leases = {r["agent_id"]: db.row_dict(r) for r in rows}
    out = []
    for agent in catalog():
        lease = leases.get(agent["id"])
        item = dict(agent)
        if lease:
            item["lease"] = lease
            item["status"] = lease["status"]
        elif agent.get("included"):
            item["status"] = "active"
            item["lease"] = {"status": "active", "since": "inklusive", "included": 1}
        else:
            item["status"] = "available"
            item["lease"] = None
        out.append(item)
    return out


def active_paid_cents(org_id: str, conn=None) -> int:
    total = 0
    for agent in fleet(org_id, conn=conn):
        lease = agent.get("lease") or {}
        if agent.get("included"):
            continue
        if lease.get("status") == "active":
            total += int(round(float(agent.get("price") or 0) * 100))
    return total


def invoice_preview(org_id: str, conn=None) -> dict[str, Any]:
    lines = []
    for agent in fleet(org_id, conn=conn):
        lease = agent.get("lease") or {}
        included = bool(agent.get("included") or lease.get("included"))
        status = lease.get("status") or agent.get("status")
        billed = status == "active" and not included
        cents = int(round(float(agent.get("price") or 0) * 100)) if billed else 0
        if status in {"active", "paused", "inklusive"} or included:
            lines.append(
                {
                    "agent_id": agent["id"],
                    "name": agent["name"],
                    "role": agent.get("role"),
                    "status": "Inklusive" if included else ("Pausiert — nicht berechnet" if status == "paused" else "Aktiv"),
                    "cents": cents,
                }
            )
    return {"lines": lines, "amount_cents": sum(l["cents"] for l in lines), "currency": "EUR"}


def _uid(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex[:12]


def german_date(value: str | None = None) -> str:
    if value and value not in {"inklusive", "—"}:
        # Keep already-formatted demo dates.
        if "." in value:
            return value
        try:
            y, m, d = value[:10].split("-")
            return f"{d}.{m}.{y}"
        except ValueError:
            return value
    today = date.today()
    return today.strftime("%d.%m.%Y")


def next_invoice_date() -> str:
    today = date.today()
    if today.month == 12:
        nxt = date(today.year + 1, 1, 1)
    else:
        nxt = date(today.year, today.month + 1, 1)
    return nxt.strftime("%d.%m.%Y")


def fleet_state(org_id: str, conn=None) -> dict[str, Any]:
    """Frontend shape: {leases: {agentId: {status, since, included}}}."""
    leases: dict[str, Any] = {}
    for agent in fleet(org_id, conn=conn):
        lease = agent.get("lease")
        if not lease:
            continue
        leases[agent["id"]] = {
            "status": lease.get("status") or agent.get("status") or "active",
            "since": lease.get("since") or "",
            "included": bool(lease.get("included") or agent.get("included")),
        }
    return {"leases": leases}


def billing_payload(org_id: str, conn=None) -> dict[str, Any]:
    preview = invoice_preview(org_id, conn=conn)
    return {
        **preview,
        "amount_eur": preview["amount_cents"] / 100.0,
        "next_invoice": next_invoice_date(),
    }


def apply_fleet_action(org_id: str, agent_id: str, action: str, conn=None) -> dict[str, Any]:
    """rent | pause | resume | cancel | reset. Raises KeyError / ValueError."""
    c = conn or db.get_conn()
    spec = by_id(agent_id) if action != "reset" else None
    if action != "reset" and not spec:
        raise KeyError(agent_id)
    if spec and spec.get("included") and action in {"pause", "resume", "cancel"}:
        raise ValueError("Der Auskunfts-Agent ist Bestandteil des Pakets.")
    if spec and spec.get("included") and action == "rent":
        return fleet_state(org_id, conn=c)

    now = db.now_iso()
    since = german_date(now)

    if action == "reset":
        c.execute(
            "UPDATE leases SET status = 'cancelled' WHERE org_id = ? AND included = 0",
            (org_id,),
        )
        return fleet_state(org_id, conn=c)

    row = c.execute(
        "SELECT * FROM leases WHERE org_id = ? AND agent_id = ?",
        (org_id, agent_id),
    ).fetchone()

    if action == "rent":
        if row:
            c.execute(
                "UPDATE leases SET status = 'active', since = ?, included = 0 WHERE id = ?",
                (since, row["id"]),
            )
        else:
            c.execute(
                "INSERT INTO leases (id, org_id, agent_id, status, since, included) VALUES (?, ?, ?, 'active', ?, 0)",
                (_uid("lease"), org_id, agent_id, since),
            )
    elif action == "pause":
        if not row or row["status"] == "cancelled":
            raise ValueError("Agent ist nicht gemietet.")
        c.execute("UPDATE leases SET status = 'paused' WHERE id = ?", (row["id"],))
    elif action == "resume":
        if not row or row["status"] == "cancelled":
            raise ValueError("Agent ist nicht gemietet.")
        c.execute("UPDATE leases SET status = 'active' WHERE id = ?", (row["id"],))
    elif action == "cancel":
        if not row or row["status"] == "cancelled":
            raise ValueError("Agent ist nicht gemietet.")
        c.execute("UPDATE leases SET status = 'cancelled' WHERE id = ?", (row["id"],))
    else:
        raise ValueError("Unbekannte Aktion.")
    return fleet_state(org_id, conn=c)
