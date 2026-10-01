# Lokaler Betrieb

Das lokale Cockpit bindet standardmäßig nur an `127.0.0.1`; sein Start ist kein
Deployment und keine Freigabe für einen Mehrbenutzer- oder Produktionsbetrieb.
Öffentlicher Betrieb verwendet ausschließlich den getrennten Adapter und Stack aus
[PUBLIC-DEPLOYMENT.md](PUBLIC-DEPLOYMENT.md). Die Offline-Demo ist eine deterministische Fixture,
kein Sprachmodell. Der Release-Nachweis qualifiziert deshalb nur die lokale Installation
und Verträge. Ein echter Backend- oder Modelllauf muss separat mit einem isolierten
Workspace und den jeweiligen Zugangsdaten geprüft werden; `model_tested` bleibt dabei
`false`, solange nur Fixtures/Verträge ausgeführt wurden.

## Einrichten und prüfen

Aus dem Vorlagenordner in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[execution]"
.\.venv\Scripts\python.exe scripts\verify_release.py
.\.venv\Scripts\python.exe -m unittest discover -v
```

`scripts/verify_release.py` erzeugt jedes Profil in einem temporären Ordner, validiert
alle vorhandenen Packs unter `agents/` und `generated/` und führt die Offline-Demo nur
für `developer` aus. Die Ausgabe ist JSON; ein fehlgeschlagener Check liefert Exit-Code 1.
Der vollständige Unittest-Lauf bleibt ein eigener Gate. Die Ausgabe behauptet keine
Produktionsquote oder fachliche Modellqualität.

Eine frische Windows-/Python-3.12-Installation einschließlich regulärem Wheel,
CLI-Demo und Launcher ist in [INSTALLATION-QUALIFICATION.md](INSTALLATION-QUALIFICATION.md)
dokumentiert. `pytest` gehört zum optionalen Extra `execution`, weil das integrierte
Testwerkzeug es im Python-Interpreter der Anwendung startet.

## Cockpit starten und stoppen

```powershell
.\Start-AI-Studio.ps1
.\Start-AI-Studio.ps1 -Port 8876
```

Der Launcher verwendet `.venv\Scripts\python.exe`, falls vorhanden, sonst `python` aus
`PATH`. Er prüft die Python-Abhängigkeiten und meldet einen konkreten manuellen
Installationsbefehl; er installiert nichts automatisch. Der Server läuft auf Loopback,
standardmäßig Port `8765`. Mit `Ctrl+C` sauber beenden.

## Öffentlichen Dienst betreiben

Der Public-Stack ist auf eine Instanz und einen festen Tenant ausgelegt. Nur der
TLS-Proxy veröffentlicht Ports; Auth-Proxy und App bleiben in privaten Netzen. Vor
jeder Bereitstellung müssen alle Containerreferenzen unveränderliche Digests besitzen,
die Secrets außerhalb von Git liegen und `/api/readiness` grün sein. Ein grüner
Liveness-Endpunkt allein reicht nicht.

Die öffentliche Sicherung umfasst das persistente `app_data`-Volume, Auditdateien und
die getrennt gesicherten CSRF-/Identity-/OIDC-/Provider-Secrets. Ohne denselben
Identity-Schlüssel lassen sich vorhandene Identitäten nicht wieder denselben opaken
Verzeichnissen zuordnen. Vor dem Snapshot App-Zugriffe anhalten oder einen atomaren
Volume-Snapshot verwenden. Restore zuerst in Staging durchführen und Login,
Nutzertrennung, Dialog, Anhang, wartende Freigabe, Auditkette und Readiness prüfen.

Prompts, Anhänge, OAuth-Cookies und Provider-Schlüssel gehören nicht in Request-Logs
oder Metriklabels. Alarmiert werden mindestens Readiness, 401/403/429-Raten,
Fehlerrate, aktive Jobs, CPU/RAM, Volume-Füllstand und fehlgeschlagene Backups.
Horizontaler Betrieb ist ohne gemeinsame Queue/Datenbank und verteilte Limits nicht
unterstützt.

## Sicherung

Den Server vor einer Sicherung stoppen. Kopiere anschließend diese Verzeichnisse in ein
zugriffsgeschütztes Backup:

- `cockpit/.runs/` ohne `providers/` (Aufträge, Dialoge, Anhänge und Freigabe-Receipts)
- `agents/` und `generated/` (Agentenpakete)
- die jeweiligen `workspace/`-Verzeichnisse (Arbeitsartefakte)

Backups dürfen keine Zugangsdaten enthalten. Prüfe vor dem Kopieren, dass keine `.env`,
API-Schlüssel, Tokens oder privaten Schlüssel im Workspace liegen. Zugangsdaten gehören in
die lokale Umgebung bzw. einen separaten Secret-Store, niemals in Aufgaben, Reports oder
Backups.

Die verschlüsselte Provider-Datei unter `cockpit/.runs/providers/` ist an das
Windows-Benutzerprofil gebunden. Für portable Backups dieses Verzeichnis auslassen
und den Provider am Ziel neu einrichten; Details in [PROVIDERS.md](PROVIDERS.md).

## Wiederherstellung aus einer Sicherung

1. Server und laufende Worker beenden. Eine Kopie während laufender Schreibvorgänge
   ist kein konsistenter Sicherungsstand.
2. Bestehende Daten am Ziel separat sichern. Agentenpakete einschließlich ihrer
   versteckten `.runs/`- und `.agents/`-Verzeichnisse, Workspaces und Cockpit-Zustand
   aus **demselben** Sicherungsstand wiederherstellen.
3. Dieselben absoluten Pfade verwenden. Dialoge, Jobs und Freigaben sind an Agenten-
   und Workspace-Pfade gebunden. Ein Umzug in einen anderen Ordner ist derzeit keine
   unterstützte Wiederherstellung; JSON-Pfade nicht manuell umschreiben.
4. Provider am Ziel erneut einrichten. Den Server starten, Dialogverlauf und einen
   Anhang-Download prüfen. Wiederhergestellte abgeschlossene Jobs dürfen nicht erneut
   starten. Wartende Freigaben müssen weiterhin dieselbe konkrete Aktion zeigen.
5. Vor Freigabe oder Wiederaufnahme den Workspace und mögliche externe Seiteneffekte
   prüfen. Eine Sicherung kann älter sein als eine bereits ausgeführte Aktion.
   Wiederherstellung macht diese Aktion nicht rückgängig und beweist nicht, dass eine
   Wiederholung sicher ist.

Ein Backup enthält vertrauliche Aufgaben und Dokumente auch ohne Provider-Schlüssel.
Es benötigt denselben Zugriffsschutz wie das Original. Die Anwendung bietet derzeit
keine automatische Sicherung, Verschlüsselung von Backups oder Pfadmigration.

`python -m unittest tests.test_backup_restore -v` prüft diesen Ablauf in einem
temporären Verzeichnis: abgeschlossener Demo-Dialog mit Anhang, wartende Freigabe,
Kopie ohne Provider-Verzeichnis, Entfernen des Originals und Rücksicherung an denselben
Pfad. Neue Manager laden Verlauf und Originalbytes ohne Dispatch; erst ausdrückliche
Freigaben setzen den wartenden Auftrag bis zum Abschluss fort. Das ist ein lokaler
Datei-/Demo-Nachweis, kein Live-Modelltest oder Nachweis externer Seiteneffekte.

## Wiederaufnahme und unbekannter Ausgang

Für `awaiting_approval` zuerst die konkrete Aktion in der Auftragsansicht prüfen und
dort freigeben oder ablehnen. Diese Pause hat noch keine ausstehende Werkzeugwirkung.
Sie verlangt keine Unterbrechungsbestätigung. Details und CLI-Beispiele stehen in
[ACTION-APPROVALS.md](ACTION-APPROVALS.md).

Nach einem Absturz zuerst den Checkpoint (`.runs/<run-id>/state.json`), die betroffenen
Dateien und externe Seiteneffekte prüfen. `in_flight` bedeutet, dass ein Schritt bereits
gestartet worden sein kann; sein Ausgang ist unbekannt. Nicht blind erneut ausführen und
keinen zweiten Schreibschritt starten, bevor die Situation geklärt ist. Erst nach einer
bewussten Prüfung mit Feedback und, falls erforderlich, der ausdrücklichen
Unterbrechungsbestätigung fortsetzen:

```powershell
python -m agentkit resume --agent generated\mein-cto --backend demo `
  --run-dir generated\mein-cto\.runs\RUN_ID `
  --feedback "Seiteneffekte geprüft; sicher fortsetzen" `
  --acknowledge-interruption
```

Ein abgeschlossener Lauf wird nicht erneut ausgeführt. Review-Evidenz ist ein strukturierter
Bericht und kein Beweis fachlicher Korrektheit; kritische Ergebnisse brauchen zusätzliche
deterministische Abnahmetests und menschliche Prüfung.
