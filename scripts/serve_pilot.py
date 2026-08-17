"""Startet die Pilot-Demo lokal und oeffnet den Browser, sobald der Server lauscht.

Bewusst ohne Abhaengigkeiten (nur Standardbibliothek) und ohne Netzzugriff:
gebunden an 127.0.0.1, damit die Demo den Rechner nicht verlaesst — das ist
dasselbe Versprechen, das der Pilot dem Kunden gibt.

Aufruf ueber PILOT_ZEIGEN.bat (Doppelklick) oder direkt:
    python scripts/serve_pilot.py [port]
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import os
import socket
import socketserver
import sys
import threading
import time
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
DEFAULT_PORT = 8777
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJECT_ROOT / "prototype"


def parse_port(argv: list[str]) -> int:
    """Portnummer aus der Kommandozeile lesen. Fehlerhafte Eingabe -> Abbruch."""
    if len(argv) < 2:
        return DEFAULT_PORT
    try:
        port = int(argv[1])
    except ValueError:
        raise SystemExit(f"[Fehler] Port muss eine Zahl sein, bekommen: {argv[1]!r}")
    if not (1024 <= port <= 65535):
        raise SystemExit(f"[Fehler] Port muss zwischen 1024 und 65535 liegen, bekommen: {port}")
    return port


def find_free_port(preferred: int) -> int:
    """Bevorzugten Port nehmen; ist er belegt, den naechsten freien suchen.

    Ein belegter Port ist der wahrscheinlichste Startfehler (ein zweites
    Demo-Fenster laeuft noch). Er darf die Vorfuehrung nicht abbrechen.
    """
    for candidate in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((HOST, candidate))
            except OSError:
                continue
            return candidate
    raise SystemExit(
        f"[Fehler] Kein freier Port zwischen {preferred} und {preferred + 19}. "
        "Bitte offene Demo-Fenster schliessen und erneut starten."
    )


def check_demo_files() -> None:
    """Fruehzeitig pruefen, statt den Kunden vor eine leere Seite zu setzen."""
    missing = [
        name
        for name in ("index.html", "app.js", "data.js", "pilot.config.js")
        if not (DEMO_DIR / name).is_file()
    ]
    if missing:
        raise SystemExit(
            f"[Fehler] In {DEMO_DIR} fehlen: {', '.join(missing)}.\n"
            "Der Projektordner ist unvollstaendig oder wurde verschoben."
        )


def read_pilot_name() -> str:
    """Firmennamen aus pilot.config.js lesen — nur fuer die Startmeldung.

    Rein kosmetisch: schlaegt es fehl, startet die Demo trotzdem.
    """
    try:
        text = (DEMO_DIR / "pilot.config.js").read_text(encoding="utf-8")
    except OSError:
        return "unbekannt"
    active = "active: true" in text
    if not active:
        return "Meridian-Standarddemo (Pilotschalter steht auf false)"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("name:"):
            return stripped.split('"')[1] if '"' in stripped else "unbekannt"
    return "unbekannt"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Wie SimpleHTTPRequestHandler, aber ohne Logzeile je Anfrage.

    Waehrend einer Vorfuehrung scrollt das Konsolenfenster sonst durch —
    sichtbar, wenn der Bildschirm geteilt wird. Fehler bleiben sichtbar.
    """

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - Signatur der Basisklasse
        status = args[1] if len(args) > 1 else ""
        if isinstance(status, str) and status.startswith(("4", "5")):
            sys.stderr.write(f"  [{status}] {args[0]}\n")

    def end_headers(self) -> None:
        # Ohne No-Cache zeigt ein zweiter Start die vorige Fassung — bei einer
        # Demo, die zwischen zwei Kundenterminen umgebrandet wird, ist das fatal.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


def open_browser_when_ready(port: int, timeout: float = 10.0) -> None:
    """Browser erst oeffnen, wenn der Server wirklich antwortet.

    PILOT_NO_BROWSER=1 unterdrueckt das Oeffnen (Rauchtest der Startkette,
    ohne ein Fenster aufzureissen).
    """
    if os.environ.get("PILOT_NO_BROWSER") == "1":
        print(f"  [Test] Browser unterdrueckt. Adresse: http://{HOST}:{port}")
        return

    waited = 0.0
    step = 0.15
    while waited < timeout:
        with contextlib.suppress(OSError):
            with socket.create_connection((HOST, port), timeout=0.5):
                webbrowser.open(f"http://{HOST}:{port}")
                return
        time.sleep(step)
        waited += step
    sys.stderr.write(
        f"  [Hinweis] Browser nicht automatisch geoeffnet. "
        f"Bitte manuell aufrufen: http://{HOST}:{port}\n"
    )


def main() -> int:
    check_demo_files()
    port = find_free_port(parse_port(sys.argv))

    print()
    print("  ============================================================")
    print(f"   PILOT-DEMO: {read_pilot_name()}")
    print("  ============================================================")
    print(f"   Adresse:  http://{HOST}:{port}")
    print("   Daten:    100 % synthetisch — kein echtes Kundendokument")
    print("   Netz:     nur dieser Rechner (127.0.0.1), nichts geht hinaus")
    print()
    print("   Beenden:  Strg+C oder dieses Fenster schliessen")
    print("  ============================================================")
    print()

    threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()

    handler = functools.partial(QuietHandler, directory=str(DEMO_DIR))
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer((HOST, port), handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Demo beendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
