# AI Studio — lokaler Arbeitsraum mit eigenen Assistenten

AI Studio verbindet eine Browseroberfläche mit portablen AgentKit-Agenten. Assistenten
anlegen, Modell und Workspace auswählen, Aufträge ausführen, Nachweise prüfen und auf
abgeschlossenen Ergebnissen aufbauen — mit dauerhaftem lokalem Verlauf.

```powershell
python -m pip install -e ".[execution]"
.\Start-AI-Studio.ps1
# http://127.0.0.1:8765
```

Der aktuelle Stand enthält zwei klar getrennte Betriebsarten. Der lokale
Single-Owner-MVP ist mit 11 von 11 verbindlichen Bereichen abgenommen. Zusätzlich
gibt es einen **öffentlichen Single-Tenant-Mehrbenutzer-Release-Candidate** hinter
OIDC- und TLS-Proxy: getrennte Nutzerzustände, CSRF- und Origin-Schutz, Rollen,
Rate- und Speichergrenzen, manipulationsgeprüfte Auditkette sowie eine gehärtete
Container-Vorlage. Im öffentlichen Modus laufen nur Demo und optional DeepSeek mit
begrenzten Text-/Dateiwerkzeugen; Codex, `run_pytest`, beliebiger Fremdcode und
binäre Anhänge sind dort gesperrt.

Der Quellstand ist lokal geprüft, aber eine konkrete Internet-Installation ist erst
nach realer OIDC-/TLS-, Backup-, Last- und unabhängiger Sicherheitsabnahme freigegeben.
Die Demo funktioniert ohne Modellzugang; reale Codex-Luna-Läufe belegen weiterhin den
separaten lokalen Modus.
Die 11/11-Zahl ist eine Funktionsumfangsquote, keine Fehlerwahrscheinlichkeit oder
Code-Coverage; aktuell gemessen sind 80 % kombinierte Line-/Branch-Coverage.
[Abnahme und offene Grenzen](docs/PRODUCT-READINESS.md),
[Betrieb und Wiederherstellung](docs/OPERATIONS.md),
[öffentliche Bereitstellung](docs/PUBLIC-DEPLOYMENT.md),
[GitHub-Auswahl](docs/GITHUB-ADOPTION.md).

DeepSeek, Codex und die Browser-Demo zeigen vor Dateiänderungen konkrete
Aktionsfreigaben. Codex liefert dafür read-only Vorschläge; ein lokaler Allowlist-
Host-Executor führt exakt bestätigte Aktionen aus. Native per-tool interception der
Codex CLI wird nicht behauptet. [Ablauf und Grenzen](docs/ACTION-APPROVALS.md).

Arbeitsdialoge unterstützen UTF-8-Textanhänge bis 32 KiB sowie PDF-, DOCX-, XLSX-
und PPTX-Dokumente bis 2 MiB. Extrahierter Text dient als Referenz; die Originaldateien
bleiben im Verlauf und lassen sich unverändert herunterladen. PNG/JPEG-Bilder
unterstützen lokale Windows-Texterkennung; das Modell erhält den erkannten Text.
Keine OCR für Scan-PDFs und keine visuelle Bildanalyse.
[Formate, Grenzen und Speicherung](docs/ATTACHMENTS.md).

DeepSeek-Zugangsdaten lassen sich unter `/settings` für das Windows-Benutzerkonto
verschlüsselt speichern. Speichern führt keinen kostenpflichtigen Modelltest aus.
[Provider-Einrichtung und Grenzen](docs/PROVIDERS.md).

Unter `/assistants` lassen sich Assistenten aus der Neuauswahl archivieren und
wiederherstellen sowie ihre Beschreibung und Vorgaben bearbeiten. Neue Aufträge
übernehmen die Änderungen; bestehende Läufe behalten ihre gespeicherten Vorgaben.
[Assistentenverwaltung](docs/ASSISTANT-MANAGEMENT.md).

Öffentliche GitHub-Textdateien lassen sich im Dialog zuerst als Vorschau laden und
dann als Quellen-Snapshot anhängen. Kein Login, keine GitHub-Schreibaktionen.
[GitHub-Connector](docs/GITHUB-CONNECTOR.md).

## AgentKit — eine Vorlage, viele Agenten

Eine gemeinsame Basis für Programmierung, Recherche, Marketing, Sales und Support.
Jeder Agent besteht aus **Identität + Rollen + ausgewählten Skills + austauschbarer Laufzeit**.
Der Workflow wählt nach jedem Ergebnis den nächsten Schritt; es gibt keine feste Kette
aus Planer, Entwickler und Tester.

Für den direkten Wiedereinstieg einer LLM steht der aktuelle Projektstand in
[`STATUS.md`](<C:/Users/botrunner/Documents/ChatGPT/AGenten vorlage/STATUS.md>).

Die Vorlage wurde auf dein Projekt `C:\Users\botrunner\projects\AI-Company` abgestimmt.
Paperclip bleibt die Company-Steuerung. Für die Ausführung gibt es einen kleinen lokalen
Runner mit Codex-Adapter sowie portable Agentenpakete für DeepSeek Harness.

## Schnellstart unter Windows

Python 3.11 oder neuer. Aus diesem Verzeichnis:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[execution]"
.\.venv\Scripts\python.exe -m agentkit profiles
.\.venv\Scripts\python.exe -m agentkit init generated\mein-cto --profile developer --name mein-cto
.\.venv\Scripts\python.exe -m agentkit run --agent generated\mein-cto --backend demo --task "Dynamischen Workflow demonstrieren"
```

Die **Offline-Demo** benötigt keinen API-Key und erzeugt `workspace/demo-result.md`.
Sie ist ein deterministischer Funktionstest, kein Sprachmodell und kein Löser beliebiger Aufgaben:
Erstellen → Review schlägt fehl → Korrektur → Review besteht → Abschluss.
Entscheidungen und Ergebnisse stehen in `.runs/<run-id>/state.json` im Agentenpaket.

Die Oberfläche **AI Studio** liegt unter `cockpit/`. Sie nutzt dieselbe Engine wie die CLI,
bietet Assistentenerstellung, Backend-/Modellauswahl, Auftragsverlauf, Folgeaufträge,
dauerhafte Dialoge unter `/chat`, Fortschritt, Nachweise, Artefakt-Downloads und
kontrollierte Wiederaufnahme. Dialoge erhalten den bisherigen sichtbaren Gesprächskontext;
bei Erreichen der Kontextgrenze wird ausdrücklich angehalten. Der Server
akzeptiert ausschließlich lokale Loopback-Adressen:

```powershell
python cockpit\server.py
# danach http://127.0.0.1:8765 öffnen
```

Die Oberfläche ist ein lokaler Bedienlayer. Company-weite Ziele und
Agentenverwaltung bleiben in Paperclip; das Cockpit eignet sich für einzelne Aufträge und
später als Paperclip-Adapter.

## Öffentlicher Mehrbenutzerbetrieb

Der öffentliche Einstiegspunkt ist `python -m cockpit.public_server`; er startet nur
mit `AGENTKIT_PUBLIC=1` und gültigen dateibasierten Secrets. Er darf ausschließlich
hinter dem mitgelieferten OIDC-/TLS-Proxy betrieben werden. Jeder Nutzer erhält einen
opaken, getrennten Agenten-, Workspace- und Zustandsbaum. Browser erhalten nur
Ressourcen-IDs, keine Hostpfade oder gespeicherten Modellfortsetzungen.

Die produktionsnahe Compose-Vorlage, die vollständige Variablenliste, Secret-Erzeugung,
Abnahmeschritte, Backup und Rollback stehen in
[docs/PUBLIC-DEPLOYMENT.md](docs/PUBLIC-DEPLOYMENT.md). Für einen sicheren ersten
Smoke-Test `AGENTKIT_PUBLIC_BACKENDS=demo` verwenden; DeepSeek erst nach Einspielen
des serververwalteten Provider-Secrets aktivieren.

In diesem Arbeitsordner sind `generated/mein-cto` und `generated/ai-studioxyz` bereits
vorbereitet. Dafür den `init`-Schritt überspringen oder einen neuen Verzeichnisnamen wählen;
vorhandene Pakete werden bewusst nicht überschrieben.

## Wirklich programmieren mit Codex

Codex CLI muss installiert und angemeldet sein. Aktuell geprüft wird CLI 0.159.2 mit
`--ignore-user-config`. `doctor` prüft die lokale Verfügbarkeit. Ein echter Lauf nutzt
standardmäßig `gpt-5.6-luna` mit niedrigem Reasoning und kann dessen Kontingent verbrauchen.

```powershell
.\.venv\Scripts\python.exe -m agentkit doctor
.\.venv\Scripts\python.exe -m agentkit run --agent generated\mein-cto --backend codex --task "Erstelle eine Python-Funktion zur Normalisierung von Telefonnummern mit dokumentiertem Eingabeformat und passenden Tests."
```

Das Arbeitsverzeichnis ist zunächst `generated/mein-cto/workspace`. Für ein vorhandenes
Repository `--workspace "C:\Pfad\zu\einem\isolierten\Checkout"` ergänzen. Für parallele
Implementierungen getrennte Git-Worktrees verwenden. `--model` ist optional; ohne Angabe
gilt `gpt-5.6-luna`. Authentifizierung bleibt erhalten. Unter Windows übernimmt der Adapter
ausschließlich die bereits eingerichtete Auswahl `[windows].sandbox` (`elevated`
oder `unelevated`); fehlt diese, bricht er vor einem Modellaufruf ab. Sonstige globale
CLI-Einstellungen werden für diesen Prozess ignoriert. Der Adapter setzt Rollen-Sandbox, Netzwerkgrenze und Modell
explizit und aktiviert keinen Fast-Tier-Aufpreis. Die globale Konfiguration bleibt unverändert.

Für einen direkten DeepSeek-API-Pilot steht zusätzlich `--backend deepseek` bereit. Dafür
`DEEPSEEK_API_KEY` nur lokal als Umgebungsvariable setzen und einen separaten Test-Workspace
verwenden. Details stehen in [docs/DEEPSEEK.md](docs/DEEPSEEK.md).

Der Koordinator läuft read-only. Schreibende Rollen nutzen `workspace-write`, Reviewer
read-only. Ein Reviewer kann für einen schreibenden Testlauf einen Entwickler-Schritt
anfordern. Der Runner verwendet keinen Sandbox-Bypass. Tools/Netzwerkzugriff außerhalb
der CLI-Sandbox hängen weiterhin von deiner Host-Konfiguration ab.

Auf der elevated-Windows-Sandbox können neu erzeugte Dateien für den Host direkt
unlesbar bleiben. AI Studio lädt ein vom Auftrag gemeldetes Codex-Artefakt in diesem
Fall über den offiziellen App-Server mit read-only-Sandbox und deaktiviertem Netzwerk.
Der Pfad bleibt auf den Workspace begrenzt; Größe, Länge und SHA-256 werden geprüft.
Der reale Qualifikationslauf schrieb und prüfte `RESULT.txt` bytegleich und exportierte
den Marker `STUDIO-FACT-4729` in 101,61 Sekunden. Details:
[Live-Qualifizierung](docs/LIVE-QUALIFICATION.md).

## DeepSeek Harness

Dein vorgeschlagener [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)
ist ein sinnvoller Ausführungshost: Plugins und native Sessions bleiben dort, unsere
Rollen und Skills bleiben portabel. Siehe den [konkreten Startweg](docs/DEEPSEEK.md).

```powershell
.\.venv\Scripts\python.exe -m agentkit native-prompt --agent generated\mein-cto --task "Untersuche die Aufgabe und waehle passende Skills. Erstelle einen kleinen getesteten Prototyp." | Set-Content -Encoding utf8 generated\mein-cto\TASK.md
```

`TASK.md` kann anschließend in der Harness-Oberfläche verwendet oder an dessen Headless-CLI
übergeben werden. Das ist **nativer Harness-Betrieb**, kein implementierter DSH-Backendadapter:
AgentKit-Limits und Sperren wirken dort nicht; die entsprechenden Regeln muss der Host tragen.

## Neue Agenten und Skills

Eine erste konkrete Ausarbeitung liegt bereits unter
[`agents/programming-agent`](<C:/Users/botrunner/Documents/ChatGPT/AGenten vorlage/agents/programming-agent>).
Sie ist der Programmier-Agent mit eigener Identität, Coding-Workflow und Review-Gate.
Der nächste konkrete Agent liegt unter
[`agents/bmd-tax-advisor`](<C:/Users/botrunner/Documents/ChatGPT/AGenten vorlage/agents/bmd-tax-advisor>).
Er ist für BMD NTCS und österreichische Steuerberatung vorbereitet, nutzt aber ohne einen
freigegebenen Adapter nur Preview-/Importpläne und keine echte Verbuchung.

| Profil | Geeignet für |
|---|---|
| `developer` | Implementierung, Debugging, Recherche und unabhängiges Review |
| `research` | Recherche mit Quellen und Entscheidungsvorlagen |
| `marketing` | Content-Entwürfe mit Recherche und Review |
| `sales` | Lead-Qualifizierung und Antwortentwürfe |
| `support` | Supportanalyse und Antwortentwürfe |
| `company` | Koordinator mit allen sieben Spezialisten |
| `bmd-tax-advisor` | BMD-Workflow, österreichische Steuerrecherche, kontrolliertes Lernen und Vier-Augen-Review |

```powershell
.\.venv\Scripts\python.exe -m agentkit init generated\mein-cmo --profile marketing --name mein-cmo --company AI_Studioxyz
.\.venv\Scripts\python.exe -m agentkit init generated\company --profile company --name company
```

Passe `SOUL.md` für Produkt, Zielgruppe und Zuständigkeiten an. `agent.json` definiert Rollen,
zugeordnete Skills, Sandbox und Limits. Die konkrete Reihenfolge entscheidet der Koordinator.

Für einen eigenen Skill kopiere `agentkit/library/skill-template` in einen neuen Ordner,
z. B. `meine-skills/python-api`. Ändere `name` in `SKILL.md` ebenfalls zu `python-api`.
Beschreibe Einsatzfall, relevante Entscheidungen, erwartetes Ergebnis und dessen Prüfung.

```powershell
.\.venv\Scripts\python.exe -m agentkit add-skill --agent generated\mein-cto --source meine-skills\python-api --role developer
.\.venv\Scripts\python.exe -m agentkit validate --agent generated\mein-cto
.\.venv\Scripts\python.exe -m agentkit inspect --agent generated\mein-cto
```

`add-skill` kopiert ein lokal geprüftes Paket und registriert es. Es installiert keine
Abhängigkeiten und führt kein `skill.py` aus. Weitere Rollen lassen sich mit einer Markdown-Datei
unter `roles/` und einem Eintrag in `agent.json` ergänzen. Kein Fork des Runners erforderlich.

## Struktur eines erzeugten Agenten

```text
mein-cto/
├── agent.json           Rollen, Skill-Zuordnung und Limits
├── STATUS.md            Aktueller Stand und LLM-Handoff
├── AGENTS.md            Gemeinsamer Arbeitsvertrag
├── SOUL.md              Identität und Company-Kontext
├── WORKFLOW.md          Dynamische Entscheidungsregeln
├── roles/              Austauschbare Spezialisten
├── .agents/skills/      Portable SKILL.md-Pakete, inklusive Herkunft/Lizenz
├── workspace/          Arbeitsergebnisse
└── .runs/              Atomare Checkpoints und Entscheidungshistorie
```

Die geteilte Python-Laufzeit liegt in `agentkit/`; `agentkit/library/` enthält die Vorlagen.
Jedes erzeugte Paket besitzt eine eigene Kopie seiner Rollen/Skills. Updates werden bewusst
übernommen, nicht während eines laufenden Auftrags still eingespielt.

`STATUS.md` ist der kanonische Einstieg für eine neue LLM-Session. Sie enthält Status,
letzten Nachweis, nächste Aktion, Blocker und Grenzen. Nach jedem relevanten Lauf wird sie
aktualisiert; die Engine validiert, dass jeder Agenten-Pack diese Datei besitzt.

## Fortsetzen und skalieren

```powershell
.\.venv\Scripts\python.exe -m agentkit resume --agent generated\mein-cto --backend codex --run-dir generated\mein-cto\.runs\RUN_ID --feedback "Der fehlende Testdienst ist jetzt erreichbar."
```

Bei einer unterbrochenen Ausführung zuerst Dateien und mögliche Seiteneffekte prüfen;
danach zusätzlich `--acknowledge-interruption` verwenden. Ein abgeschlossener Lauf wird
nicht erneut ausgeführt. Verbrauchte Laufzeit, Schritte und Fehler bleiben beim Fortsetzen
erhalten. Limits werden bewusst in `agent.json` geändert, nicht durch einen Retry zurückgesetzt.

Innerhalb eines Workspace laufen Schritte nacheinander. Separate Instanzen in separaten
Workspaces können unabhängig laufen. Für Company-weite Warteschlangen, Budgets, Heartbeats
und Zuständigkeiten Paperclip nutzen: [Integration in AI-Company](docs/AI-COMPANY.md).
Für verteilte Worker/Container braucht es zusätzliche Isolation und einen zentralen Scheduler.

## Nachweise und Grenzen

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

- Die Offline-Demo und automatisierten Tests prüfen Routing, Review, Limits, Checkpoints,
  Sperren, Skill-Validierung und Adapterverträge.
- Aktueller Gesamtstand: 352 Tests in 248,693 Sekunden mit
  Branch-Coverage-Instrumentierung, `OK`, drei erwartete
  Windows-Symlink-Skips; fünf echte isolierte Chromium-Journeys, 80 % kombinierte
  Line-/Branch-Coverage, Ruff, Bandit ohne mittlere/hohe Befunde, zehn
  Workflow-Trace-Szenarien und 19/19
  Offline-Release-Checks mit echter lokaler Windows-OCR bestanden
  (`offline_only=true`, `model_tested=false`).
- Der Codex-Adapter ist gegen die installierte CLI-Hilfe und mit Prozess-/Vertragstests geprüft.
  Ein vollständiger gpt-5.6-luna/low-Live-Schreibablauf bestand am 30.09.2026 mit
  isolierter Konfiguration, elevated-Windows-Sandbox, Python-Byteprüfung,
  unabhängigem Review und sicherem Artefaktexport. Reale Repository-, Test-Recovery-
  und GitHub-Connector-Aufgaben bestanden ebenfalls. Der gehärtete Planner-Abbruch/
  Resume-Lauf terminierte den Kindprozess, verweigerte die unbestätigte Wiederaufnahme
  und schloss nach Bestätigung mit unverändertem Workspace ab.
  Aktuelle Nachweise und die verbleibenden Gates stehen in
  [docs/PRODUCT-READINESS.md](docs/PRODUCT-READINESS.md).
- DeepSeek-Startbefehle und Skill-Verzeichnisse sind aus dem Upstream-Quellcode abgeleitet;
  DSH wurde hier nicht installiert oder live ausgeführt. Developer-Preview-APIs können wechseln.
- Review-Evidenz ist ein strukturierter Agentenbericht, kein kryptografischer Erfolgsbeweis.
  Der Runner prüft Schema und Artefaktexistenz; fachliche Korrektheit muss geprüft werden.
- Rollen-/Skill-Auswahl ist keine Betriebssystem-Sicherheitsgrenze. Native Tools und
  Hostberechtigungen bleiben entscheidend. Zeit-/Schrittlimits sind kein Euro-Budget.
- Checkpoints enthalten Aufgaben und Ergebnisse lokal unverschlüsselt. Keine Credentials
  in Aufgaben oder Berichte schreiben. Sie werden durch `.gitignore` vom normalen Commit ausgeschlossen.

[Architektur](docs/ARCHITECTURE.md) · [GitHub-Auswahl und Quellen](docs/RESEARCH.md)
