# Installation aus einer frischen Python-Umgebung

Am 30.09.2026 unter Windows mit Python 3.12.8 geprüft. Die neue virtuelle Umgebung
hat `include-system-site-packages = false`; vorhandene globale Python-Pakete wurden
nicht übernommen. Keine Modellaufrufe oder echten Zugangsdaten verwendet.

## Ausgeführte Abnahme

1. `python -m venv .runs/qualification/clean-install-venv`
2. Installation mit dem Python dieser Umgebung über `-m pip install .`.
   Dabei wurde ein reguläres Wheel gebaut und installiert, keine Editable-Verknüpfung.
3. `python -I -m agentkit init ... --profile developer --name install-check` und
   `python -I -m agentkit run ... --backend demo --task "Installation qualification"`.
   `-I` verhindert den Import aus dem aktuellen Quellverzeichnis. Der überprüfte
   Importpfad lag unter `clean-install-venv/Lib/site-packages/agentkit`.
4. Separater Quellordner mit `agentkit/`, `cockpit/` und `Start-AI-Studio.ps1`, ohne
   bestehende Zustandsdaten. Launcher mit dem frischen Python auf PATH und Port 8879
   gestartet. Health-API, Assistentenerstellung und HTTP-Demoauftrag bestanden;
   Ergebnis `completed`, `reviewed = true`. Testserver anschließend beendet.
5. `pip check`, vollständige Unittests und `scripts/verify_release.py` mit dem
   Python der frischen Umgebung ausgeführt. Diese Tests verwenden den Quellbaum;
   die davon getrennte Wheel-Abnahme steht in Schritt 3.

Der erste Wheel-Demostart deckte einen Fehler auf: Die CLI übergab `model` auch an
`DemoBackend`, dessen Konstruktor kein Argument akzeptiert. Der Aufruf ist korrigiert;
das Wheel wurde neu installiert und der isolierte Lauf bestand. Neue Subprozesstests
prüfen CLI-Init, Demoabschluss, idempotenten Resume und beide konkreten Freigaben.

Der erste vollständige Testlauf fand außerdem eine fehlende Laufzeitabhängigkeit:
`run_pytest` verwendet den Python-Interpreter der Anwendung, aber `pytest` war nicht
als Abhängigkeit eingetragen. Nun wird es mitinstalliert und vom Launcher geprüft.
Der fehlgeschlagene Erstlauf bleibt im Log nachvollziehbar; die abschließende Prüfung
steht in `clean-install-unittest-final.log`.

## Nachweise und Grenzen

Lokale Nachweise liegen unter `.runs/qualification/clean-install-*`: Installationslogs,
Demo-JSON, HTTP-Ergebnis, vollständiger Testlauf und Release-JSON. Installiert wurden
unter anderem PyYAML 6.0.3, jsonschema 4.26.0, pypdf 6.19.0, defusedxml 0.7.1
und pytest 9.1.1.
`pip check` meldete keine defekten Abhängigkeiten.
Der abschließende Gesamtlauf bestand mit 140 Tests in 49,274 Sekunden; alle 17
Offline-Release-Checks und Ruff bestanden ebenfalls.

Der unterstützte AI-Studio-Start benötigt weiterhin den Quellordner samt `cockpit/`
und Launcher. Das Python-Wheel liefert AgentKit, keine eigenständige Desktop-App.
Die Abnahme gilt für diese Windows-/Python-Kombination und die aufgelösten Pakete;
eine Prüfung aller Betriebssysteme oder aller Versionen innerhalb der erlaubten
Abhängigkeitsbereiche wird daraus nicht abgeleitet. Live-Modellbetrieb bleibt separat
in [LIVE-QUALIFICATION.md](LIVE-QUALIFICATION.md) beschrieben.
