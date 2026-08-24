"""Public catalog of rentable digital employees (list prices, no payment).

Prices are list prices matching the pilot one-pager tone. No Stripe or live
payment capture belongs in this module — the rental ledger stores the price
for display and future billing only.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


# List prices in EUR (Decimal strings for JSON-safe money).
_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "agent_id": "controlling",
        "label": "Controlling-Agent",
        "description": (
            "Monatsbericht und Kennzahlen-Abgleich aus Saldenliste und "
            "Belegen — der provisionierbare Pilot-Agent."
        ),
        "monthly_price_eur": "400",
        "preset_id": "kmu-controlling",
        "provisionable": True,
    },
    {
        "agent_id": "reporting",
        "label": "Reporting-Agent",
        "description": (
            "Vorstands- und Monatsberichte auf Knopfdruck aus der "
            "Wissensbasis — minimale Instanz ohne Controlling-Preset."
        ),
        "monthly_price_eur": "400",
        "preset_id": None,
        "provisionable": True,
    },
    {
        "agent_id": "rechnungen",
        "label": "Rechnungs-Agent",
        "description": (
            "Prüft Belege, Drei-Wege-Abgleich und Abweichungen. "
            "Katalog-Eintrag — Provisionierung folgt mit eigenem Pack."
        ),
        "monthly_price_eur": "600",
        "preset_id": None,
        "provisionable": False,
    },
    {
        "agent_id": "vertraege",
        "label": "Vertrags-Agent",
        "description": (
            "Überwacht Fristen, Verlängerungen und Klauseln. "
            "Katalog-Eintrag — Provisionierung folgt mit eigenem Pack."
        ),
        "monthly_price_eur": "500",
        "preset_id": None,
        "provisionable": False,
    },
)


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe catalog dict (prices as Decimal strings)."""
    price = entry["monthly_price_eur"]
    normalized = format(Decimal(price), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return {
        "agent_id": entry["agent_id"],
        "label": entry["label"],
        "description": entry["description"],
        "monthly_price_eur": normalized,
        "preset_id": entry["preset_id"],
        "provisionable": bool(entry["provisionable"]),
    }


def list_agents() -> list[dict[str, Any]]:
    """Return the deterministic public catalog of rentable agents."""
    return [_public_entry(entry) for entry in _CATALOG]


def get_agent(agent_id: str) -> dict[str, Any] | None:
    """Look up one catalog entry by agent_id, or None if unknown."""
    if not isinstance(agent_id, str):
        return None
    for entry in _CATALOG:
        if entry["agent_id"] == agent_id:
            return _public_entry(entry)
    return None
