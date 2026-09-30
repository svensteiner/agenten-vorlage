# Prüfstand — 17.09.2026

Ausgeführt unter Windows mit Python 3.12.8:

| Prüfung | Ergebnis |
|---|---|
| `python -m unittest discover -q` | **43 Tests bestanden** |
| `python -m ruff check agentkit tests cockpit` | Bestanden |
| DeepSeek-Backend ohne Netzlauf | Strukturierter API-Vertrag per Mock getestet; Schlüssel bleibt nur im Prozess |
| Echte DeepSeek-API mit Programming-Agent | Isolierte Sandbox erfolgreich; Programming-Agent gegen Pseudokrat bewusst nicht bestanden (Baseline-Fehler blieb offen; Agent erzeugte einmal einen unvollständigen Diff, der zurückgesetzt wurde) |
| Python-Kompilierung (`agentkit`, `cockpit`) | Bestanden |
| Entwickler- und Company-Paket erzeugen/validieren | Bestanden |
| Lokale CLI-Demo | 5 Entscheidungen; Review-Fehler, Korrektur, erfolgreicher Abschluss |
| Wheel bauen | `dist/company_agentkit-0.1.0-py3-none-any.whl` erzeugt |
| Wheel inklusive Abhängigkeiten separat installieren | Bestanden |
| Isolierter Import aus Wheel-Installation | Alle 6 Profile erzeugt; Demo abgeschlossen |
| Vendortes Superpowers-Skill | SHA-256 stimmt mit UPSTREAM.json überein; MIT-Lizenz enthalten |
| Codex-CLI | Lokal vorhanden; verwendete Optionen mit `codex exec --help` geprüft |

Die Tests umfassen unter anderem Review-Invalidierung, dynamische Nacharbeit, read-only
Recherche ohne Coding-Pipeline, unbekannte Rollen/Skills, Artefaktpfade, Limits, Prozess-Timeout,
Workspace-Sperre, unterbrochene Aufrufe, Resume-Grenzen und die Paperclip-Übersetzungsfunktionen.

Der direkte DeepSeek-Adapter nutzt `/chat/completions`, JSON-Modus für Planerantworten, robuste Tool-Argumente und
Function-Tools für Workspace-Intake, Dateiänderungen und pytest. Der Workspace-Leser unterstützt UTF-8 und CP1252. Interne Lock-Dateien werden
nicht als Projektdateien exponiert; nicht parsebare Markdown-JSON-Antworten werden sicher erkannt.

Der echte Smoke-Test lief in `C:\\Users\\botrunner\\projects\\deepseek-coding-sandbox-4`.
Er erzeugte `phone_utils.py` und `test_phone_utils.py`; der unabhängige Reviewer bestätigte
alle Abnahmekriterien und reproduzierte `23 passed`. Der verwendete Schlüssel wurde nicht
in Dateien geschrieben oder in der Ausgabe ausgegeben.

Nicht ausgeführt: nativer DeepSeek-Harness-Lauf, Live-Paperclip-Updates, Linux-CI.
Die CI-Konfiguration deckt Windows/Linux und Python 3.11/3.12 ab; sie wurde lokal nicht als
GitHub-Actions-Lauf ausgeführt. AI-Company wurde nicht verändert oder neu gestartet.

