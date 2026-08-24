"""Catalog of rentable agents: list prices, no payment capture."""

from __future__ import annotations

import json

from core.agent_catalog import get_agent, list_agents


def test_list_agents_is_deterministic_json_safe():
    first = list_agents()
    second = list_agents()
    assert first == second
    raw = json.dumps(first, ensure_ascii=False, separators=(",", ":"))
    restored = json.loads(raw)
    assert restored == first
    ids = [entry["agent_id"] for entry in first]
    assert ids == ["controlling", "reporting", "rechnungen", "vertraege"]


def test_controlling_is_provisionable_kmu_preset_at_400():
    agent = get_agent("controlling")
    assert agent is not None
    assert agent["label"] == "Controlling-Agent"
    assert agent["monthly_price_eur"] == "400"
    assert agent["preset_id"] == "kmu-controlling"
    assert agent["provisionable"] is True
    assert isinstance(agent["monthly_price_eur"], str)


def test_reporting_is_provisionable_generic_pack():
    agent = get_agent("reporting")
    assert agent is not None
    assert agent["monthly_price_eur"] == "400"
    assert agent["preset_id"] is None
    assert agent["provisionable"] is True


def test_invoice_and_contract_agents_are_catalog_only():
    invoices = get_agent("rechnungen")
    contracts = get_agent("vertraege")
    assert invoices is not None and contracts is not None
    assert invoices["monthly_price_eur"] == "600"
    assert contracts["monthly_price_eur"] == "500"
    assert invoices["provisionable"] is False
    assert contracts["provisionable"] is False
    assert invoices["preset_id"] is None
    assert contracts["preset_id"] is None
    assert invoices["cta_label"] == "Vormerken — Pack folgt"
    assert contracts["cta_label"] == "Vormerken — Pack folgt"
    assert "noch nicht öffenbar" in invoices["description"]
    assert get_agent("controlling")["cta_label"] == "Mieten"
    assert get_agent("reporting")["cta_label"] == "Mieten"


def test_unknown_and_non_string_agent_ids_return_none():
    assert get_agent("unknown-agent") is None
    assert get_agent("../controlling") is None
    assert get_agent("") is None
    assert get_agent(None) is None  # type: ignore[arg-type]
