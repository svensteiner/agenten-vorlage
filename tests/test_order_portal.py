"""HTTP contract tests for the localhost-only zero-cost order portal."""

from __future__ import annotations

import http.client
import json
from pathlib import Path
import socket
import threading
from urllib.parse import urlsplit

import pytest

from order_portal import create_server


@pytest.fixture
def portal(tmp_path: Path):
    server = create_server(data_root=tmp_path / "portal-data", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    origin = f"http://{host}:{port}"
    try:
        yield origin
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _request(
    origin: str,
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
):
    parsed = urlsplit(origin)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=30)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = dict(headers or {})
    if body is not None:
        request_headers.setdefault("Content-Type", "application/json")
        request_headers.setdefault("Content-Length", str(len(body)))
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    data = response.read()
    response_headers = {name.lower(): value for name, value in response.getheaders()}
    connection.close()
    return response.status, response_headers, data


def _session(origin: str) -> str:
    status, _, raw = _request(origin, "GET", "/api/session")
    assert status == 200
    return json.loads(raw)["csrf_token"]


def _request_bytes(
    origin: str,
    method: str,
    path: str,
    body: bytes,
    *,
    headers: dict[str, str],
):
    parsed = urlsplit(origin)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=30)
    request_headers = {
        **headers,
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
    }
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    data = response.read()
    status = response.status
    connection.close()
    return status, data


def _raw_http(origin: str, request: bytes) -> bytes:
    parsed = urlsplit(origin)
    with socket.create_connection((parsed.hostname, parsed.port), timeout=10) as stream:
        stream.sendall(request)
        chunks: list[bytes] = []
        while True:
            chunk = stream.recv(4096)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)


def _mutation_headers(origin: str, csrf: str) -> dict[str, str]:
    return {"Origin": origin, "X-CSRF-Token": csrf}


def test_portal_uses_restrictive_headers_and_no_cors(portal):
    status, headers, body = _request(portal, "GET", "/")

    assert status == 200
    assert b"Sehen Sie heute, wo Ihr Unternehmen steht." in body
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert "access-control-allow-origin" not in headers


def test_mutation_requires_same_origin_csrf_and_json(portal):
    payload = {
        "company_name": "Muster Demo GmbH",
        "idempotency_key": "checkout-portal-001",
        "synthetic_only": True,
        "confirmed_zero_cost": True,
    }

    status, _, _ = _request(portal, "POST", "/api/demo-orders", payload=payload)
    assert status == 403

    csrf = _session(portal)
    status, _, _ = _request(
        portal,
        "POST",
        "/api/demo-orders",
        payload=payload,
        headers={"Origin": portal, "X-CSRF-Token": "wrong"},
    )
    assert status == 403

    status, _, _ = _request(
        portal,
        "POST",
        "/api/demo-orders",
        payload=payload,
        headers=_mutation_headers(portal, csrf),
    )
    assert status == 201


def test_rejected_mutation_closes_connection_and_rejects_expect_continue(portal):
    payload = {
        "company_name": "Muster Demo GmbH",
        "idempotency_key": "checkout-portal-001",
        "synthetic_only": True,
        "confirmed_zero_cost": True,
    }
    status, headers, _ = _request(
        portal,
        "POST",
        "/api/demo-orders",
        payload=payload,
        headers={"Origin": "https://attacker.invalid"},
    )
    assert status == 403
    assert headers["connection"] == "close"

    csrf = _session(portal)
    status, headers, _ = _request(
        portal,
        "POST",
        "/api/demo-orders",
        payload=payload,
        headers={
            **_mutation_headers(portal, csrf),
            "Expect": "100-continue",
        },
    )
    assert status == 417
    assert headers["connection"] == "close"


@pytest.mark.parametrize("length", ["²", "9" * 5_000])
def test_portal_rejects_unbounded_or_non_ascii_content_length(portal, length):
    csrf = _session(portal)
    status, headers, _ = _request(
        portal,
        "POST",
        "/api/demo-orders",
        payload={
            "company_name": "Muster Demo GmbH",
            "idempotency_key": "checkout-portal-001",
            "synthetic_only": True,
            "confirmed_zero_cost": True,
        },
        headers={
            **_mutation_headers(portal, csrf),
            "Content-Length": length,
        },
    )

    assert status == 411
    assert headers["connection"] == "close"


def test_portal_rejects_invalid_unicode_company_name_without_dropping_response(
    portal,
):
    csrf = _session(portal)
    status, _, raw = _request(
        portal,
        "POST",
        "/api/demo-orders",
        payload={
            "company_name": "\ud800",
            "idempotency_key": "checkout-portal-001",
            "synthetic_only": True,
            "confirmed_zero_cost": True,
        },
        headers=_mutation_headers(portal, csrf),
    )

    assert status == 400
    assert "ungültige Zeichen" in json.loads(raw)["error"]


def test_portal_returns_controlled_400_for_malformed_absolute_request_target(portal):
    parsed = urlsplit(portal)
    raw = _raw_http(
        portal,
        (
            "GET http://[::1 HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii"),
    )

    assert raw.startswith(b"HTTP/1.1 400")


def test_portal_returns_controlled_400_for_deeply_nested_json(portal):
    csrf = _session(portal)
    body = b"[" * 8_000 + b"0" + b"]" * 8_000

    status, raw = _request_bytes(
        portal,
        "POST",
        "/api/demo-orders",
        body,
        headers=_mutation_headers(portal, csrf),
    )

    assert status == 400
    assert json.loads(raw)["error"] == "JSON ist ungültig."


def test_api_completes_real_order_to_accepted_report_journey(portal):
    csrf = _session(portal)
    headers = _mutation_headers(portal, csrf)
    create_status, _, raw_order = _request(
        portal,
        "POST",
        "/api/demo-orders",
        payload={
            "company_name": "Muster Demo GmbH",
            "idempotency_key": "checkout-portal-001",
            "synthetic_only": True,
            "confirmed_zero_cost": True,
        },
        headers=headers,
    )
    order = json.loads(raw_order)

    assert create_status == 201
    assert order["status"] == "ready"
    assert order["cost"]["budget_eur"] == "0"
    order_id = order["order_id"]

    verify_status, _, raw_verified = _request(
        portal,
        "POST",
        f"/api/demo-orders/{order_id}/verify",
        payload={"idempotency_key": "verify-portal-001"},
        headers=headers,
    )
    verified = json.loads(raw_verified)

    assert verify_status == 200
    assert verified["status"] == "accepted"
    assert verified["acceptance"]["passed"] is True
    assert verified["acceptance"]["repeatable_run_count"] == 3

    report_status, report_headers, report = _request(
        portal, "GET", f"/api/demo-orders/{order_id}/report"
    )
    assert report_status == 200
    assert report_headers["content-type"].startswith("text/html")
    assert b"<title>KMU-Controlling-Report</title>" in report
    assert b"Saldenliste_Muster_Juni2026.xlsx" in report


@pytest.mark.parametrize(
    "path",
    [
        "/api/demo-orders/../report",
        "/api/demo-orders/%2e%2e/report",
        "/api/demo-orders/%252e%252e/report",
        r"/api/demo-orders/..%5creport",
        "/api/demo-orders/C:%5cWindows/report",
        "//server/share",
    ],
)
def test_portal_rejects_traversal_and_unknown_routes(portal, path):
    status, _, _ = _request(portal, "GET", path)
    assert status in {400, 404}


def test_agents_catalog_endpoint_is_local_json(portal):
    status, headers, raw = _request(portal, "GET", "/api/agents")
    payload = json.loads(raw)
    assert status == 200
    assert headers["x-content-type-options"] == "nosniff"
    ids = [item["agent_id"] for item in payload["agents"]]
    assert ids == ["controlling", "reporting", "rechnungen", "vertraege"]
    controlling = payload["agents"][0]
    assert controlling["monthly_price_eur"] == "400"
    assert controlling["provisionable"] is True


def test_rental_mutation_requires_same_origin_csrf(portal):
    payload = {
        "company_name": "Muster Demo GmbH",
        "agent_id": "controlling",
        "idempotency_key": "rent-portal-001",
    }
    status, _, _ = _request(portal, "POST", "/api/rentals", payload=payload)
    assert status == 403

    csrf = _session(portal)
    status, _, raw = _request(
        portal,
        "POST",
        "/api/rentals",
        payload=payload,
        headers=_mutation_headers(portal, csrf),
    )
    assert status == 201
    rental = json.loads(raw)
    assert rental["status"] == "active"
    assert rental["agent_id"] == "controlling"
    assert rental["spent_eur"] == "0"


def test_rental_api_rent_list_cancel_flow(portal):
    csrf = _session(portal)
    headers = _mutation_headers(portal, csrf)
    create_status, _, raw = _request(
        portal,
        "POST",
        "/api/rentals",
        payload={
            "company_name": "Muster Demo GmbH",
            "agent_id": "reporting",
            "idempotency_key": "rent-portal-reporting-001",
        },
        headers=headers,
    )
    rental = json.loads(raw)
    assert create_status == 201
    tenant_id = rental["tenant_id"]

    list_status, _, listed_raw = _request(
        portal, "GET", f"/api/rentals?tenant_id={tenant_id}"
    )
    listed = json.loads(listed_raw)
    assert list_status == 200
    assert listed["tenant_id"] == tenant_id
    assert listed["rentals"][0]["rental_id"] == rental["rental_id"]
    assert listed["rentals"][0]["status"] == "active"

    by_company_status, _, by_company_raw = _request(
        portal,
        "GET",
        "/api/rentals?company_name=Muster%20Demo%20GmbH",
    )
    assert by_company_status == 200
    assert json.loads(by_company_raw)["rentals"][0]["rental_id"] == rental["rental_id"]

    cancel_status, _, cancelled_raw = _request(
        portal,
        "POST",
        f"/api/rentals/{rental['rental_id']}/cancel",
        payload={
            "tenant_id": tenant_id,
            "idempotency_key": "cancel-portal-001",
        },
        headers=headers,
    )
    cancelled = json.loads(cancelled_raw)
    assert cancel_status == 200
    assert cancelled["status"] == "cancelled"

    replay_status, _, replay_raw = _request(
        portal,
        "POST",
        f"/api/rentals/{rental['rental_id']}/cancel",
        payload={
            "tenant_id": tenant_id,
            "idempotency_key": "cancel-portal-001",
        },
        headers=headers,
    )
    assert replay_status == 200
    assert json.loads(replay_raw)["cancelled_at"] == cancelled["cancelled_at"]


def test_rental_api_rejects_unknown_agent_and_missing_tenant(portal):
    csrf = _session(portal)
    headers = _mutation_headers(portal, csrf)
    status, _, raw = _request(
        portal,
        "POST",
        "/api/rentals",
        payload={
            "company_name": "Muster Demo GmbH",
            "agent_id": "payroll",
            "idempotency_key": "rent-portal-unknown",
        },
        headers=headers,
    )
    assert status == 400
    assert "Unbekannter Agent" in json.loads(raw)["error"]

    status, _, _ = _request(portal, "GET", "/api/rentals")
    assert status == 400


def test_demo_order_journey_still_works_alongside_rentals(portal):
    csrf = _session(portal)
    headers = _mutation_headers(portal, csrf)
    rent_status, _, _ = _request(
        portal,
        "POST",
        "/api/rentals",
        payload={
            "company_name": "Muster Demo GmbH",
            "agent_id": "rechnungen",
            "idempotency_key": "rent-portal-invoices",
        },
        headers=headers,
    )
    assert rent_status == 201

    create_status, _, raw_order = _request(
        portal,
        "POST",
        "/api/demo-orders",
        payload={
            "company_name": "Muster Demo GmbH",
            "idempotency_key": "checkout-portal-with-rentals",
            "synthetic_only": True,
            "confirmed_zero_cost": True,
        },
        headers=headers,
    )
    order = json.loads(raw_order)
    assert create_status == 201
    assert order["cost"]["budget_eur"] == "0"
    assert order["profile"] == "deterministic_local_demo"


def _rent(portal, csrf, agent_id, key):
    status, _, raw = _request(
        portal,
        "POST",
        "/api/rentals",
        payload={
            "company_name": "Muster Demo GmbH",
            "agent_id": agent_id,
            "idempotency_key": key,
        },
        headers=_mutation_headers(portal, csrf),
    )
    assert status == 201
    return json.loads(raw)


def test_open_route_serves_cockpit_for_provisioned_rental(portal):
    csrf = _session(portal)
    rental = _rent(portal, csrf, "controlling", "rent-open-controlling-001")
    open_path = (
        f"/api/rentals/{rental['rental_id']}/open?tenant_id={rental['tenant_id']}"
    )
    status, headers, _ = _request(portal, "GET", open_path)
    assert status == 302
    location = headers["location"]
    assert location == (
        f"/api/rentals/{rental['rental_id']}/cockpit/{rental['tenant_id']}/"
    )

    page_status, page_headers, page = _request(portal, "GET", location)
    assert page_status == 200
    assert "text/html" in page_headers["content-type"]
    assert b"AI Studio" in page
    assert b"app.js" in page
    assert "script-src 'self'" in page_headers["content-security-policy"]

    asset_status, asset_headers, asset = _request(
        portal, "GET", f"{location}app.js"
    )
    assert asset_status == 200
    assert "javascript" in asset_headers["content-type"]
    assert asset

    config_status, _, config = _request(
        portal, "GET", f"{location}pilot.config.js"
    )
    assert config_status == 200
    assert b"window.PILOT_CONFIG" in config
    assert rental["display_name"].encode("utf-8") in config


def test_open_route_rejects_cancelled_rental(portal):
    csrf = _session(portal)
    headers = _mutation_headers(portal, csrf)
    rental = _rent(portal, csrf, "reporting", "rent-open-reporting-001")
    cancel_status, _, _ = _request(
        portal,
        "POST",
        f"/api/rentals/{rental['rental_id']}/cancel",
        payload={
            "tenant_id": rental["tenant_id"],
            "idempotency_key": "cancel-open-001",
        },
        headers=headers,
    )
    assert cancel_status == 200
    status, _, raw = _request(
        portal,
        "GET",
        f"/api/rentals/{rental['rental_id']}/open?tenant_id={rental['tenant_id']}",
    )
    assert status == 409
    assert "gekuendigt" in json.loads(raw)["error"]


def test_open_route_rejects_ledger_only_rental(portal):
    csrf = _session(portal)
    rental = _rent(portal, csrf, "rechnungen", "rent-open-invoices-001")
    status, _, raw = _request(
        portal,
        "GET",
        f"/api/rentals/{rental['rental_id']}/open?tenant_id={rental['tenant_id']}",
    )
    assert status == 409
    assert "Pack folgt" in json.loads(raw)["error"]


def test_open_route_rejects_wrong_tenant(portal):
    csrf = _session(portal)
    rental = _rent(portal, csrf, "controlling", "rent-open-wrong-tenant-001")
    status, _, raw = _request(
        portal,
        "GET",
        f"/api/rentals/{rental['rental_id']}/open?tenant_id=other-kmu",
    )
    assert status == 404
    assert json.loads(raw)["error"] == "Miete nicht gefunden."


def test_open_route_rejects_path_escape(tmp_path):
    server = create_server(data_root=tmp_path / "portal-data", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    origin = f"http://{host}:{port}"
    try:
        csrf = _session(origin)
        rental = _rent(origin, csrf, "controlling", "rent-open-escape-001")
        record = (
            tmp_path
            / "portal-data"
            / "rentals"
            / ".ledger"
            / "rentals"
            / rental["tenant_id"]
            / f"{rental['rental_id']}.json"
        )
        state = json.loads(record.read_text(encoding="utf-8"))
        state["instance_path"] = "../escape"
        record.write_text(
            json.dumps(state, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        status, _, raw = _request(
            origin,
            "GET",
            f"/api/rentals/{rental['rental_id']}/open?tenant_id={rental['tenant_id']}",
        )
        assert status == 409
        assert "Instanzpfad" in json.loads(raw)["error"]

        forbidden_status, _, _ = _request(
            origin,
            "GET",
            f"/api/rentals/{rental['rental_id']}/cockpit/{rental['tenant_id']}/../app.js",
        )
        assert forbidden_status in {400, 404}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_open_route_requires_tenant(portal):
    csrf = _session(portal)
    rental = _rent(portal, csrf, "controlling", "rent-open-missing-tenant-001")
    status, _, _ = _request(
        portal, "GET", f"/api/rentals/{rental['rental_id']}/open"
    )
    assert status == 400
