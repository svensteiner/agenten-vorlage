"""Hardened localhost portal for the synthetic KMU controlling demo."""

from __future__ import annotations

from decimal import Decimal
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import re
import secrets
import unicodedata
from urllib.parse import urlsplit

from core.local_kmu_orders import (
    LocalKmuOrderService,
    OrderConflict,
    OrderNotFound,
    OrderValidationError,
)
from core.rentals import (
    RentalConflict,
    RentalNotFound,
    RentalNotOpenable,
    RentalService,
    RentalValidationError,
)


_PORTAL_ROOT = Path(__file__).resolve().parent / "order-portal"
_PROTOTYPE_ROOT = Path(__file__).resolve().parent / "prototype"
_ORDER_ROUTE = re.compile(r"^/api/demo-orders/(ord_[0-9a-f]{32})$")
_VERIFY_ROUTE = re.compile(r"^/api/demo-orders/(ord_[0-9a-f]{32})/verify$")
_REPORT_ROUTE = re.compile(r"^/api/demo-orders/(ord_[0-9a-f]{32})/report$")
_RENTAL_CANCEL_ROUTE = re.compile(
    r"^/api/rentals/(rnt_[0-9a-f]{32})/cancel$"
)
_RENTAL_OPEN_ROUTE = re.compile(
    r"^/api/rentals/(rnt_[0-9a-f]{32})/open$"
)
_COCKPIT_INDEX_ROUTE = re.compile(
    r"^/api/rentals/(rnt_[0-9a-f]{32})/cockpit/([a-z][a-z0-9-]{0,62})/?$"
)
_COCKPIT_ASSET_ROUTE = re.compile(
    r"^/api/rentals/(rnt_[0-9a-f]{32})/cockpit/"
    r"([a-z][a-z0-9-]{0,62})/([A-Za-z0-9._-]+)$"
)
_COCKPIT_ASSETS = {
    "index.html": ("index.html", "text/html; charset=utf-8"),
    "app.js": ("app.js", "text/javascript; charset=utf-8"),
    "data.js": ("data.js", "text/javascript; charset=utf-8"),
    "styles.css": ("styles.css", "text/css; charset=utf-8"),
}
_MAX_REQUEST_BYTES = 16 * 1024
_STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}


def _bound_host_port(server: ThreadingHTTPServer) -> tuple[str, int]:
    address = server.server_address
    raw_host = address[0]
    host = (
        bytes(raw_host).decode("ascii")
        if isinstance(raw_host, (bytes, bytearray))
        else str(raw_host)
    )
    return host, address[1]


def _technical_tenant_id(company_name: str) -> str:
    try:
        encoded_name = company_name.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise OrderValidationError("Firmenname enthält ungültige Zeichen.") from exc
    normalized = unicodedata.normalize("NFKD", company_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not slug or not slug[0].isalpha():
        slug = f"kmu-{slug}".strip("-")
    digest = hashlib.sha256(encoded_name).hexdigest()[:8]
    return f"{slug[:45].rstrip('-')}-{digest}"


class _PortalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        server_address: tuple[str, int],
        service: LocalKmuOrderService,
        rental_service: RentalService,
    ):
        self.order_service = service
        self.rental_service = rental_service
        self.csrf_token = secrets.token_urlsafe(32)
        super().__init__(server_address, _PortalHandler)


class _PortalHandler(BaseHTTPRequestHandler):
    server: _PortalServer
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _expected_origin(self) -> str:
        host, port = _bound_host_port(self.server)
        return f"http://{host}:{port}"

    def _security_headers(self, *, report: bool = False) -> dict[str, str]:
        if report:
            policy = (
                "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
            )
        else:
            policy = (
                "default-src 'none'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
                "form-action 'self'; frame-ancestors 'none'"
            )
        return {
            "Cache-Control": "no-store",
            "Content-Security-Policy": policy,
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }

    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str,
        *,
        report: bool = False,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if self.close_connection:
            self.send_header("Connection", "close")
        for name, value in self._security_headers(report=report).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict[str, object]) -> None:
        raw = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        self._send(status, raw, "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self.close_connection = True
        self._json(status, {"error": message})

    def handle_expect_100(self) -> bool:
        self._error(
            HTTPStatus.EXPECTATION_FAILED,
            "Expect: 100-continue ist für die lokale Demo nicht erlaubt.",
        )
        return False

    def _request_is_local(self) -> bool:
        try:
            return ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            return False

    def _valid_host(self) -> bool:
        return self.headers.get("Host") == self._expected_origin().removeprefix(
            "http://"
        )

    def _safe_path(self) -> str | None:
        try:
            raw_path = urlsplit(self.path).path
        except ValueError:
            return None
        lowered = raw_path.lower()
        if (
            not raw_path.startswith("/")
            or raw_path.startswith("//")
            or "\\" in raw_path
            or ".." in raw_path
            or ":" in raw_path
            or any(token in lowered for token in ("%2e", "%2f", "%5c", "%25"))
        ):
            return None
        return raw_path

    def _preflight(self) -> str | None:
        if not self._request_is_local() or not self._valid_host():
            self._error(HTTPStatus.BAD_REQUEST, "Ungültige lokale Anfrage.")
            return None
        path = self._safe_path()
        if path is None:
            self._error(HTTPStatus.BAD_REQUEST, "Ungültiger Pfad.")
        return path

    def _read_mutation_json(self) -> dict[str, object] | None:
        if self.headers.get("Origin") != self._expected_origin():
            self._error(HTTPStatus.FORBIDDEN, "Lokale Herkunft fehlt.")
            return None
        if self.headers.get("X-CSRF-Token") != self.server.csrf_token:
            self._error(HTTPStatus.FORBIDDEN, "Sicherheits-Token ist ungültig.")
            return None
        if self.headers.get("Transfer-Encoding") is not None:
            self._error(HTTPStatus.BAD_REQUEST, "Transfer-Encoding ist nicht erlaubt.")
            return None
        lengths = self.headers.get_all("Content-Length", [])
        if (
            len(lengths) != 1
            or len(lengths[0]) > 6
            or not lengths[0].isascii()
            or not lengths[0].isdecimal()
        ):
            self._error(HTTPStatus.LENGTH_REQUIRED, "Content-Length fehlt.")
            return None
        length = int(lengths[0])
        if length < 2 or length > _MAX_REQUEST_BYTES:
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Anfrage ist zu groß.")
            return None
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if media_type.lower() != "application/json":
            self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "JSON ist erforderlich.")
            return None
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
            self._error(HTTPStatus.BAD_REQUEST, "JSON ist ungültig.")
            return None
        if not isinstance(payload, dict):
            self._error(HTTPStatus.BAD_REQUEST, "JSON-Objekt ist erforderlich.")
            return None
        return payload

    def do_GET(self) -> None:  # noqa: N802
        path = self._preflight()
        if path is None:
            return
        if path in _STATIC_FILES:
            filename, media_type = _STATIC_FILES[path]
            target = _PORTAL_ROOT / filename
            try:
                body = target.read_bytes()
            except OSError:
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Portal fehlt.")
                return
            self._send(HTTPStatus.OK, body, media_type)
            return
        if path == "/healthz":
            self._json(HTTPStatus.OK, {"status": "ready"})
            return
        if path == "/api/session":
            self._json(
                HTTPStatus.OK,
                {
                    "csrf_token": self.server.csrf_token,
                    "profile": "deterministic_local_demo",
                    "budget_eur": "0",
                },
            )
            return
        order_match = _ORDER_ROUTE.fullmatch(path)
        if order_match:
            self._serve_order(order_match.group(1))
            return
        report_match = _REPORT_ROUTE.fullmatch(path)
        if report_match:
            self._serve_report(report_match.group(1))
            return
        if path == "/api/agents":
            self._serve_agents()
            return
        if path == "/api/rentals":
            self._serve_rentals()
            return
        open_match = _RENTAL_OPEN_ROUTE.fullmatch(path)
        if open_match:
            self._open_rental(open_match.group(1))
            return
        asset_match = _COCKPIT_ASSET_ROUTE.fullmatch(path)
        if asset_match:
            self._serve_cockpit(
                asset_match.group(1),
                asset_match.group(2),
                asset_match.group(3),
            )
            return
        cockpit_match = _COCKPIT_INDEX_ROUTE.fullmatch(path)
        if cockpit_match:
            if not path.endswith("/"):
                self._redirect(f"{path}/")
                return
            self._serve_cockpit(
                cockpit_match.group(1),
                cockpit_match.group(2),
                "index.html",
            )
            return
        self._error(HTTPStatus.NOT_FOUND, "Route nicht gefunden.")

    def do_POST(self) -> None:  # noqa: N802
        path = self._preflight()
        if path is None:
            return
        payload = self._read_mutation_json()
        if payload is None:
            return
        if path == "/api/demo-orders":
            self._create_order(payload)
            return
        if path == "/api/rentals":
            self._create_rental(payload)
            return
        match = _VERIFY_ROUTE.fullmatch(path)
        if match:
            self._verify_order(match.group(1), payload)
            return
        cancel_match = _RENTAL_CANCEL_ROUTE.fullmatch(path)
        if cancel_match:
            self._cancel_rental(cancel_match.group(1), payload)
            return
        self._error(HTTPStatus.NOT_FOUND, "Route nicht gefunden.")

    def _create_order(self, payload: dict[str, object]) -> None:
        if (
            payload.get("synthetic_only") is not True
            or payload.get("confirmed_zero_cost") is not True
        ):
            self._error(
                HTTPStatus.BAD_REQUEST,
                "Diese Demo arbeitet nur mit fiktiven Daten und 0 EUR Budget.",
            )
            return
        company_name = payload.get("company_name")
        idempotency_key = payload.get("idempotency_key")
        if not isinstance(company_name, str) or not isinstance(
            idempotency_key, str
        ):
            self._error(HTTPStatus.BAD_REQUEST, "Firmenname und Schlüssel fehlen.")
            return
        try:
            order = self.server.order_service.create_order(
                tenant_id=_technical_tenant_id(company_name),
                agent_id="controlling",
                idempotency_key=idempotency_key,
                display_name=company_name,
                budget_eur=Decimal("0"),
            )
        except OrderValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except OrderConflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except OSError:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Lokale Bestellung konnte nicht gespeichert werden.",
            )
            return
        self._json(HTTPStatus.CREATED, order)

    def _serve_order(self, order_id: str) -> None:
        try:
            order = self.server.order_service.get_order_by_id(order_id)
        except OrderNotFound:
            self._error(HTTPStatus.NOT_FOUND, "Bestellung nicht gefunden.")
            return
        except OrderConflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except OSError:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Lokale Bestellung konnte nicht gelesen werden.",
            )
            return
        self._json(HTTPStatus.OK, order)

    def _verify_order(
        self, order_id: str, payload: dict[str, object]
    ) -> None:
        idempotency_key = payload.get("idempotency_key")
        if not isinstance(idempotency_key, str):
            self._error(HTTPStatus.BAD_REQUEST, "Prüfschlüssel fehlt.")
            return
        try:
            order = self.server.order_service.verify_order_by_id(
                order_id=order_id, idempotency_key=idempotency_key
            )
        except OrderValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except OrderNotFound:
            self._error(HTTPStatus.NOT_FOUND, "Bestellung nicht gefunden.")
            return
        except OrderConflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except OSError:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Lokale Prüfung konnte nicht gespeichert werden.",
            )
            return
        self._json(HTTPStatus.OK, order)

    def _serve_report(self, order_id: str) -> None:
        try:
            report = self.server.order_service.read_report_html_by_id(order_id)
        except OrderNotFound:
            self._error(HTTPStatus.NOT_FOUND, "Bestellung nicht gefunden.")
            return
        except OrderConflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except OSError:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Lokaler Bericht konnte nicht gelesen werden.",
            )
            return
        self._send(
            HTTPStatus.OK,
            report,
            "text/html; charset=utf-8",
            report=True,
        )



    def _tenant_from_payload(
        self, payload: dict[str, object]
    ) -> tuple[str, str] | None:
        company_name = payload.get("company_name")
        tenant_id = payload.get("tenant_id")
        display_name = payload.get("display_name")
        if tenant_id is not None and not isinstance(tenant_id, str):
            self._error(HTTPStatus.BAD_REQUEST, "tenant_id ist ungueltig.")
            return None
        if company_name is not None and not isinstance(company_name, str):
            self._error(HTTPStatus.BAD_REQUEST, "Firmenname ist ungueltig.")
            return None
        if display_name is not None and not isinstance(display_name, str):
            self._error(HTTPStatus.BAD_REQUEST, "Anzeigename ist ungueltig.")
            return None
        if not tenant_id:
            if not company_name:
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "tenant_id oder Firmenname fehlt.",
                )
                return None
            try:
                tenant_id = _technical_tenant_id(company_name)
            except OrderValidationError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return None
        resolved_name = display_name or company_name or tenant_id
        return tenant_id, resolved_name

    def _serve_agents(self) -> None:
        self._json(
            HTTPStatus.OK,
            {"agents": self.server.rental_service.list_catalog()},
        )

    def _tenant_from_query(self) -> str | None:
        from urllib.parse import parse_qs

        query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
        tenant_values = query.get("tenant_id", [])
        company_values = query.get("company_name", [])
        tenant_id = tenant_values[0] if len(tenant_values) == 1 else ""
        company_name = company_values[0] if len(company_values) == 1 else ""
        if not tenant_id:
            if not company_name:
                self._error(HTTPStatus.BAD_REQUEST, "tenant_id fehlt.")
                return None
            try:
                tenant_id = _technical_tenant_id(company_name)
            except OrderValidationError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return None
        return tenant_id

    def _redirect(self, location: str) -> None:
        if not location.startswith("/api/rentals/"):
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Weiterleitung ist ungueltig.",
            )
            return
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        if self.close_connection:
            self.send_header("Connection", "close")
        for name, value in self._security_headers().items():
            self.send_header(name, value)
        self.end_headers()

    def _open_rental(self, rental_id: str) -> None:
        tenant_id = self._tenant_from_query()
        if tenant_id is None:
            return
        try:
            rental = self.server.rental_service.open_rental(tenant_id, rental_id)
        except RentalValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except RentalNotFound:
            self._error(HTTPStatus.NOT_FOUND, "Miete nicht gefunden.")
            return
        except RentalNotOpenable as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except RentalConflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except OSError:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Miete konnte nicht geoeffnet werden.",
            )
            return
        self._redirect(
            f"/api/rentals/{rental['rental_id']}/cockpit/{rental['tenant_id']}/"
        )

    def _serve_cockpit(
        self, rental_id: str, tenant_id: str, filename: str
    ) -> None:
        try:
            rental = self.server.rental_service.open_rental(tenant_id, rental_id)
        except RentalValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except RentalNotFound:
            self._error(HTTPStatus.NOT_FOUND, "Miete nicht gefunden.")
            return
        except RentalNotOpenable as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except RentalConflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except OSError:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Cockpit konnte nicht gelesen werden.",
            )
            return
        if filename == "pilot.config.js":
            config = {
                "active": True,
                "company": {
                    "name": rental["display_name"],
                    "tagline": "Lokale gemietete Instanz",
                },
            }
            body = (
                "window.PILOT_CONFIG = "
                + json.dumps(config, ensure_ascii=False, separators=(",", ":"))
                + ";\n"
            ).encode("utf-8")
            self._send(HTTPStatus.OK, body, "text/javascript; charset=utf-8")
            return
        spec = _COCKPIT_ASSETS.get(filename)
        if spec is None:
            self._error(HTTPStatus.NOT_FOUND, "Route nicht gefunden.")
            return
        disk_name, media_type = spec
        target = _PROTOTYPE_ROOT / disk_name
        try:
            resolved = target.resolve(strict=True)
            resolved.relative_to(_PROTOTYPE_ROOT.resolve(strict=True))
        except (OSError, ValueError):
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Cockpit fehlt.")
            return
        if resolved.parent != _PROTOTYPE_ROOT.resolve(strict=True):
            self._error(HTTPStatus.NOT_FOUND, "Route nicht gefunden.")
            return
        try:
            body = resolved.read_bytes()
        except OSError:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Cockpit fehlt.")
            return
        self._send(HTTPStatus.OK, body, media_type)

    def _serve_rentals(self) -> None:
        tenant_id = self._tenant_from_query()
        if tenant_id is None:
            return
        try:
            rentals = self.server.rental_service.list_rentals(tenant_id)
        except RentalValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except RentalConflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except OSError:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Mieten konnten nicht gelesen werden.",
            )
            return
        self._json(HTTPStatus.OK, {"tenant_id": tenant_id, "rentals": rentals})

    def _create_rental(self, payload: dict[str, object]) -> None:
        resolved = self._tenant_from_payload(payload)
        if resolved is None:
            return
        tenant_id, display_name = resolved
        agent_id = payload.get("agent_id")
        idempotency_key = payload.get("idempotency_key")
        if not isinstance(agent_id, str) or not isinstance(idempotency_key, str):
            self._error(HTTPStatus.BAD_REQUEST, "agent_id und Schluessel fehlen.")
            return
        try:
            rental = self.server.rental_service.rent(
                tenant_id=tenant_id,
                agent_id=agent_id,
                display_name=display_name,
                idempotency_key=idempotency_key,
            )
        except RentalValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except RentalConflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except OSError:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Miete konnte nicht gespeichert werden.",
            )
            return
        self._json(HTTPStatus.CREATED, rental)

    def _cancel_rental(
        self, rental_id: str, payload: dict[str, object]
    ) -> None:
        idempotency_key = payload.get("idempotency_key")
        if not isinstance(idempotency_key, str):
            self._error(HTTPStatus.BAD_REQUEST, "Kuendigungsschluessel fehlt.")
            return
        tenant_id = payload.get("tenant_id")
        company_name = payload.get("company_name")
        if not isinstance(tenant_id, str) or not tenant_id:
            if not isinstance(company_name, str) or not company_name:
                self._error(HTTPStatus.BAD_REQUEST, "tenant_id fehlt.")
                return
            try:
                tenant_id = _technical_tenant_id(company_name)
            except OrderValidationError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
        try:
            rental = self.server.rental_service.cancel(
                tenant_id=tenant_id,
                rental_id=rental_id,
                idempotency_key=idempotency_key,
            )
        except RentalValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except RentalNotFound:
            self._error(HTTPStatus.NOT_FOUND, "Miete nicht gefunden.")
            return
        except RentalConflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except OSError:
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Kuendigung konnte nicht gespeichert werden.",
            )
            return
        self._json(HTTPStatus.OK, rental)


def create_server(
    *, data_root: Path, host: str = "127.0.0.1", port: int = 0
) -> _PortalServer:
    """Create, but do not start, the localhost-only demo server."""
    if host != "127.0.0.1":
        raise ValueError("Das Demo-Portal darf nur auf 127.0.0.1 laufen.")
    service = LocalKmuOrderService(Path(data_root) / "instances")
    rental_service = RentalService(Path(data_root) / "rentals")
    return _PortalServer((host, port), service, rental_service)


def main() -> int:
    import argparse
    import webbrowser

    parser = argparse.ArgumentParser(
        description="Kostenfreie lokale Demo des KMU-Controlling-Agenten"
    )
    parser.add_argument(
        "--data-root", type=Path, default=Path("work") / "order-portal"
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = create_server(data_root=args.data_root, port=args.port)
    host, port = _bound_host_port(server)
    origin = f"http://{host}:{port}"
    print(f"Demo läuft lokal unter {origin}")
    print("Nur synthetische Daten, keine Zahlung, keine externen Aktionen.")
    if not args.no_browser:
        webbrowser.open(origin)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
