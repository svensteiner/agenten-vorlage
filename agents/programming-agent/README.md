# Programming Agent — erste Ausarbeitung

Dieser Ordner ist der erste konkrete Spezialagent unter der Agenten-Vorlage. Er ist für
Softwareentwicklung in einem separat zugewiesenen Workspace gedacht und nutzt die gemeinsame
AgentKit-Laufzeit. Das Paket ist bewusst klein gehalten, damit Rollen und Skills später ohne
Code-Kopie erweitert werden können.

## Was der Agent macht

- versteht einen Programmierauftrag anhand des vorhandenen Repositories;
- wählt dynamisch zwischen Recherche, Implementierung, Debugging und Review;
- arbeitet mit kleinen, überprüfbaren Änderungen;
- führt passende Tests aus und meldet echte Evidenz;
- lässt Codeänderungen vor dem Abschluss durch eine separate read-only Rolle prüfen.

Der Agent darf lokal entwickeln und testen. Deployments, Veröffentlichungen, externe Nachrichten,
Käufe und irreversible Datenänderungen bleiben außerhalb dieses ersten Agenten. In AI_Studioxyz
bleibt Paperclip für Aufgabenbesitz und Sven für Go-live-Gates zuständig.

## Produktionsregeln für Coding-Läufe

Der Agent liest `STATUS.md` im Ziel-Workspace vor dem ersten Edit und hält sie nach jedem
wesentlichen Schritt aktuell. Bestehende große Dateien werden über gezielte exakte Edits geändert;
ein vollständiges Überschreiben aus einer Teilansicht wird vom DeepSeek-Adapter blockiert. Nach
Unterbrechungen wird der Checkpoint zuerst inspiziert und nur mit neuem Feedback fortgesetzt.

## Reale Ausfuehrungsabnahme am 12.10.2026

Ein isolierter Bugfix-Auftrag mit Codex `gpt-5.6-luna` wurde abgeschlossen
(`1f030bb10e4b45d2a7ed50d870bd7676`, drei Rollen-/Planungsschritte, Review bestanden).
Vorher scheiterten zwei von drei unveraenderten Tests; danach bestanden alle drei,
sowohl im hostseitigen `run_pytest` als auch bei separater `unittest`-Nachpruefung.
Der Lauf erforderte konkretes Feedback zu gemischten Zeilenenden nach drei abgewiesenen
Edits. Er belegt einen echten Python-Bugfix, keine allgemeine Autonomiequote.
Die Wiederholungsabnahme `7f459565f22340b3abb71860087feacb` bestand danach ohne
inhaltliches Korrekturfeedback: gezielter Edit, drei Tests, selbststaendige Nacharbeit
am Statusbericht nach Review und erneutes erfolgreiches Review (fuenf Schritte).
Der Host gab ausschliesslich Aktionen im isolierten Testprojekt frei; die Testdatei
blieb bytegenau unveraendert. Mangels Git-Baseline konnte der Reviewer dies nur anhand
der verfuegbaren Aktionshistorie beurteilen; die separate Hostpruefung bestaetigte es.
Die anschliessende Git-Abnahme bestand mit committed Ausgangsstand: genau eine
Codeaenderung, erfolgreicher Test, separates Review des echten Diffs, bytegenaues
Ergebnis und unveraenderte Testdatei. Ein zweiter Lauf bestaetigte null Aenderungen
nach abgewiesener Schreibfreigabe. Nachweis und Grenzen:
[`docs/CODING-AGENT-ACCEPTANCE.md`](../../docs/CODING-AGENT-ACCEPTANCE.md).
Der Codex-Worker darf mit nativen read-only Werkzeugen untersuchen; Schreib- und
Testaktionen werden weiterhin vom Host nach Freigabe ausgefuehrt. Einheitliche
CRLF-Dateien behalten ihre Zeilenenden bei LF-formatierten Edit-Vorschlaegen.

## Offline-Schnelltest

Aus dem Root der Agenten-Vorlage:

```powershell
python -m agentkit validate --agent agents\programming-agent
python -m agentkit inspect --agent agents\programming-agent
python -m agentkit run --agent agents\programming-agent --backend demo --task "Zeige den dynamischen Programmier-Workflow"
```

Die Demo ist kein echter Coding-Lauf. Sie prüft nur, dass ein Artefakt nach einem fehlgeschlagenen
Review gezielt überarbeitet und danach erneut geprüft wird. Der Checkpoint liegt in
`agents/programming-agent/.runs/` und ist durch `.gitignore` ausgeschlossen.

## Echter Coding-Lauf mit Codex

Codex CLI installieren und anmelden, dann für ein echtes Repository einen isolierten Workspace
angeben:

```powershell
& .\Start-Coding-Agent.ps1 -Workspace "C:\Pfad\zum\projekt-worktree"
```

Ein konkreter Arbeitsauftrag kann direkt mitgegeben werden:

```powershell
& .\Start-Coding-Agent.ps1 -Workspace "C:\Pfad\zum\projekt-worktree" `
  -Task "Behebe den beschriebenen Fehler, ergaenze passende Tests und pruefe den Diff."
```

Der Auftrag erscheint editierbar in AI Studio. Dort startest du ihn und siehst
die konkreten Schreib-/Testvorschlaege, Ergebnisse und Review-Schritte.

Weitere Modellanbieter: `-Backend api` verwendet eine frei konfigurierte
Chat-Completions-API; `-Backend deepseek` verwendet den bisherigen DeepSeek-Zugang.
`-Backend anthropic` verwendet die native Messages-API und standardmaessig Haiku 4.5.
Konfiguration und Protokollgrenzen: [docs/MODEL-APIS.md](../../docs/MODEL-APIS.md).

Der Launcher oeffnet die Browseroberflaeche mit diesem Agenten, Codex und einem
test-/revieworientierten Startauftrag. Der direkte CLI-Weg bleibt ebenfalls verfuegbar:

```powershell
python -m agentkit run `
  --agent agents\programming-agent `
  --backend codex `
  --workspace C:\Users\botrunner\projects\mein-projekt-worktree `
  --task "Implementiere die beschriebene Änderung, teste sie und liefere einen überprüfbaren Diff."
```

Der Agentenordner selbst ist Konfiguration und Skill-Katalog. Der zu ändernde Code gehört in
`--workspace`, idealerweise in einen eigenen Git-Worktree. Ohne `--workspace` würde nur der
interne `workspace/`-Ordner als Scratch-Bereich verwendet.

## Erste sinnvolle Erweiterungen

1. Einen projektspezifischen Skill für die AI-Company-Toolchain hinzufügen, etwa `paperclip-agent`.
2. Sprach-/Framework-Skills ergänzen, wenn ein konkretes Repository sie benötigt.
3. Für CMO, CSO und CSM jeweils ein eigenes Paket aus derselben Basis erzeugen.
4. Erst danach einen Paperclip-Heartbeat anschließen; dabei den vorhandenen Checkout-/Run-Lifecycle
   weiterverwenden und keinen zweiten globalen Poller starten.
