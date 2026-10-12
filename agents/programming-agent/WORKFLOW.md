# Dynamic programming workflow

Der Standardpfad ist eine Orientierung, keine starre Pipeline:

`Auftrag verstehen → Repository untersuchen → kleinste Änderung wählen → implementieren →
gezielt prüfen → separate read-only Prüfung → abschließen oder nacharbeiten`

Der tatsächliche nächste Schritt hängt vom letzten Ergebnis ab. Eine reine Recherche endet
nach der belastbaren Antwort. Ein bereits reproduzierter Fehler kann direkt in Debugging gehen.
Ein fehlgeschlagenes Review führt nur zu der betroffenen Korrektur und danach zu einem neuen Review.

## Intake

Vor dem ersten Schreibschritt klären:

- Welche Datei, Schnittstelle oder Nutzerhandlung soll sich ändern?
- Woran erkennt man Erfolg? Formuliere mindestens ein konkretes Abnahmeartefakt.
- Welche Repository-Regeln, Tests und Toolchain gelten bereits?
- Welche Dateien gehören zum Auftrag und welche fremden Änderungen müssen unangetastet bleiben?

Wenn eine fehlende Information die Implementierung wesentlich ändern würde, blockieren und die
Frage präzise formulieren. Reversible Stilentscheidungen selbst treffen und dokumentieren.

## Umsetzung

Lies bestehende Aufrufer und ähnliche funktionierende Stellen vor einer neuen Abstraktion.
Halte die Änderung klein, synchronisiere betroffene Verträge und fasse keine unabhängigen
Refactorings an. Bei einem Fehler zuerst reproduzieren und die Ursache untersuchen; nicht mehrere
unbelegte Reparaturen stapeln.

## Prüfung

Führe die engsten sinnvollen Tests zuerst aus und erweitere nur bei begründetem Risiko. Prüfe
auch Fehlerpfade und die tatsächliche Diff. Ein Schreibschritt setzt das Review-Gate zurück.
Abschluss erst nach einer frischen Prüfung durch die separate read-only Reviewer-Rolle mit konkreter Evidenz.

## Bericht

Melde `status`, `summary`, `artifacts`, `evidence` und `next_actions`. Verweise auf relative
Dateipfade im Workspace. Trenne ausgeführt, nicht ausgeführt und angenommen. Bei Blockade nenne
Ursache, sichere nächste Untersuchung und Stop-Bedingung.

The local runtime offers delegate, finish and blocked. The planner chooses one action per
iteration. Workers are sequential within one workspace; independent agent instances can run
in separate worktrees/processes. Do not create recursive delegation trees inside a worker.

Limits on decisions, failed steps, call duration and context size live in agent.json.
Hitting a limit yields blocked with a checkpoint. Time/step limits are not monetary budgets;
Paperclip or the model provider must enforce spend limits.

For native DeepSeek Harness, load the dynamic-workflow skill and use the harness's own
tools, subagents and trajectory. The Python runner's hard checks do not apply to native mode.

