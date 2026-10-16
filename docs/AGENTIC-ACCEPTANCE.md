# Abnahme der Agentenvorlagen

Ziel: Die Agenten sollen einen Auftrag mit passenden Skills selbst planen,
ausführen, prüfen und bei behebbaren Fehlern nacharbeiten. Die Bewertung gilt
für die direkte eigene Nutzung von Coding- und Marketingagenten; die spätere
Mietplattform ist ein eigener Auftrag. Eine Prozentzahl allein beweist diese
Fähigkeiten nicht. Der Gesamtabschluss ist noch nicht nachgewiesen.

| Anforderung | Nachweis / verbleibende Lücke |
|---|---|
| Austauschbare Rollen, Skills und Firmenbindung | Generierte Pakete und Katalogprüfungen im Release-Gate; keine ausführbaren Skill-Plugins |
| Wahl des nächsten Schritts aus Beobachtungen | Engine und Backend-Vertrag; Offline-Demo ist lediglich eine Fixture |
| Werkzeuge tatsächlich ausführen | Host-Executor und API-Adapter; Live-Nachweis muss Modell, Aufgabe und Lauf identifizieren |
| Nach einem verfrühten Abschluss selbst nacharbeiten | Neue Engine-Tests: fehlende Evidenz nachholen, unabhängiges Review nachholen, wiederholte Ablehnung begrenzen |
| Änderungen unabhängig prüfen | Review-Gate; jede mögliche Änderung entwertet das frühere Review |
| Keine unbekannten Seiteneffekte wiederholen | Persistiertes `in_flight`, Bindung und bewusste Wiederaufnahme; bestehende Resume-Tests bleiben verbindlich |
| Anbieter wechseln und Ressourcen begrenzen | Explizite API-/Codex-Adapter, Zeit-, Schritt- und Fehlerbudgets; Provider-Fixtures sind keine Live-Abnahme |
| Ziele vollständig erfüllen statt nur Erfolg melden | Belegter Abschlussbericht und Review sind Mindestbedingungen; fachliche Abnahmekriterien müssen zusätzlich am tatsächlichen Ergebnis geprüft werden |
| Einen realen Coding-Auftrag unbeaufsichtigt erledigen | Kleine bisherige Live-Fixtures reichen nicht für beliebige Projekte; repräsentative Projektaufgaben und Regressionstests fehlen als umfassender Nachweis |
| Marketinginhalte belastbar verbessern | Die bisherige Blindabnahme ist gescheitert; echte neue Ausgabequalität und unveränderte Veröffentlichungsschutzmechanismen müssen noch nachgewiesen werden |
| Mit einem anderen Skill eine andere Fachrolle ausüben | Paketkomposition vorhanden; erfolgreiche Coding-Aufgaben belegen keine steuerliche oder andere fachliche Richtigkeit |

## Nachweise vom 16.10.2026

- Die drei neuen Verhaltenstests scheiterten vor der Engine-Änderung und bestanden
  danach. Zusammen mit den bisherigen Engine-Tests bestanden 62 Tests.
- Die gesamte Testsuite führte mit Coverage 408 Tests aus und maß für die Engine
  92 % kombinierte Line-/Branch-Coverage. Ein intermittierender Browser-Test war
  fehlerhaft; das ist ausdrücklich kein vollständig grüner Gesamtlauf.
- Der Browser-Test wartete vor seiner zweiten Freigabe noch nicht auf eine neue
  Freigabe-ID. Nach Korrektur bestanden beide öffentlichen Browser-Tests. Es
  wurden keine Produktfreigaben automatisiert oder Prüfungen übersprungen.
- 20 Offline-Release-Gates bestanden, einschließlich generierter Pakete und Demo.
- Echter Modellpfad: `codex`, Modell `gpt-6-luna`, isolierter temporärer Workspace,
  höchstens 300 Sekunden und 90 Sekunden pro Aufruf. Der erfolgreiche Lauf
  benötigte 59,484 Sekunden, vier Schritte und zwei Berichte; ein separates Review
  bestand. Der Host bestätigte identische Eingabe-/Ergebnisbytes über den
  read-only Sandbox-Export und eine unveränderte Eingabe.
- Zwei vorausgehende Modellversuche wurden nicht als Erfolge gezählt. Im zweiten
  meldete das Modell, es könne einen weiteren Reviewer nicht starten. Die
  Rollenbeschreibung stellt nun klar, dass die aktuelle Reviewer-Instanz bereits
  vom Host unabhängig dispatcht wird und die Prüfung selbst durchführen soll.

Die Belege liegen privat unter `.runs/qualification/agentic-*20261016*`.
Diese Prüfung belegt den konkreten Dateiauftrag und die geänderte Fehlerbehandlung,
keinen unbeaufsichtigten Erfolg für beliebige Projekte und keine verbesserte
Marketingqualität. Der endgültige Gesamtlauf nach der Browser-Testkorrektur
bestand: **408 Tests ausgeführt, drei übersprungen, keine Fehler**, in
220,472 Sekunden. Der vorherige fehlgeschlagene Lauf bleibt als Beleg erhalten.
Das unabhängige Review und Ruff fanden keine blockierenden Befunde.

Verbindliche Prüfungen bei Laufzeitänderungen:

```powershell
python -m unittest discover -v
python scripts/verify_release.py
```

Hinzu kommen ein unabhängiges Code-Review und ein ausdrücklich als solcher
gekennzeichneter echter Modelllauf. Dessen Ergebnis ist auf die konkrete Aufgabe
und den verwendeten Anbieter begrenzt. Ein gescheiterter Live-Lauf wird mit seiner
Fehlerkategorie dokumentiert und nicht durch eine Offline-Demo ersetzt.

Für die Produktabnahme bleiben alle Anforderungen dieser Tabelle offen, bis ihre
jeweiligen aktuellen Nachweise geprüft sind. Einzelne grüne Tests erlauben keine
pauschale Aussage „100 Prozent autonom“ oder „produktionsreif“.
