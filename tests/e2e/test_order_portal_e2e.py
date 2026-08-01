"""Real browser journey from demo order to the generated report."""

from __future__ import annotations

import ipaddress
from pathlib import Path
import threading
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from order_portal import create_server


def test_customer_orders_runs_and_opens_real_controlling_report(tmp_path: Path):
    server = create_server(data_root=tmp_path / "portal-data", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    origin = f"http://{host}:{port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000}
            )
            page = context.new_page()
            external_attempts: list[str] = []

            def block_external(route):
                target = urlsplit(route.request.url)
                try:
                    address = ipaddress.ip_address(target.hostname or "")
                except ValueError:
                    external_attempts.append(route.request.url)
                    route.abort()
                    return
                if not address.is_loopback:
                    external_attempts.append(route.request.url)
                    route.abort()
                    return
                route.continue_()

            context.route("**/*", block_external)
            page.goto(origin, wait_until="networkidle")
            page.get_by_label("Firmenname der Demo").fill("Muster Demo GmbH")
            page.get_by_label("Nur fiktive Beispieldaten verwenden").check()
            page.get_by_role(
                "button", name="Kostenlose Demo bestellen"
            ).click()
            page.get_by_text("Kundenbereich bereit").wait_for(timeout=30_000)

            page.get_by_role("button", name="Agent vollständig prüfen").click()
            page.get_by_text("Bericht bereit · 3/3 geprüft").wait_for(
                timeout=90_000
            )

            page.reload(wait_until="networkidle")
            page.get_by_text("Kundenbereich bereit").wait_for(timeout=30_000)
            page.get_by_text("Bericht bereit · 3/3 geprüft").wait_for(
                timeout=30_000
            )

            with page.expect_popup() as popup:
                page.get_by_role("button", name="Managementbericht öffnen").click()
            report = popup.value
            report.wait_for_load_state("domcontentloaded")
            assert report.title() == "KMU-Controlling-Report"
            assert report.get_by_role(
                "heading", name="KMU-Controlling-Report"
            ).is_visible()
            assert report.get_by_text(
                "Saldenliste_Muster_Juni2026.xlsx", exact=False
            ).first.is_visible()
            assert external_attempts == []
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
