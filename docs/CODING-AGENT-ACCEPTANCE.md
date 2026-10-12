# Coding-Agent: reale Abnahme am 12.10.2026

Der lokale Coding-Agent nimmt konkrete Auftraege ueber AI Studio oder die CLI an,
untersucht den zugewiesenen Workspace, schlaegt gezielte Aenderungen vor, fuehrt
hostseitige Tests aus und laesst das Ergebnis separat read-only pruefen.
Codex verwendet standardmaessig `gpt-5.6-luna` mit niedriger Reasoning-Stufe.

## Nachweise

- Vollstaendige Regression: 379 Tests bestanden, drei erwartete Windows-Symlink-Skips;
  kombinierte Line-/Branch-Coverage 80 %. CI fuer Runtime-Commit `67642b7` erfolgreich.
- Reale Bugfix-Abnahme `7f459565f22340b3abb71860087feacb`: gemischte Zeilenenden,
  gezielter Edit, drei unveraenderte Tests, Statusaktualisierung, selbststaendige
  Nacharbeit nach Review, erneutes Review bestanden. Kein inhaltliches Operatorfeedback.
- `scripts/live_codex_approval_smoke.py --live --model gpt-5.6-luna`
  mit `--call-timeout 120 --max-seconds 600`: `passed=true`, Gesamtzeit 238,36 Sekunden.
  Im Git-Projekt wurde ausschliesslich `app.py` geaendert, dessen SHA-256 exakt mit
  dem erwarteten Ergebnis uebereinstimmte. Hosttest und unabhaengiger pytest-Aufruf
  bestanden; separate Reviewer-Rolle pruefte `git status` und `git diff HEAD`.
  Zwei Freigaben, zwei intakte Auditeintraege, kein Replay. Der Ablehnungsfall hatte
  eine protokollierte Ablehnung und null Dateiaenderungen.
- Lokale maschinenlesbare Evidenz:
  `.runs/qualification/codex-git-baseline-20261012.json`.

## Eigener Auftrag

Native Anthropic-Abnahme am 12.10.2026: Haiku 4.5 bestand Run
`dd23c252e06347fc9879c3fb34cd7aee` in einem isolierten Git-Testprojekt.
Der Host genehmigte einen exakten `edit_file`-Vorschlag fuer `app.py` und einen
`run_pytest`-Aufruf. Ein Test bestand, das separate read-only Review bestaetigte
Diff und Testnachweis. Ergebnisbytes entsprachen exakt der erwarteten Korrektur;
nur `app.py` war geaendert. Testdatei und STATUS.md blieben unveraendert.
Maschinenlesbare lokale Evidenz: `.runs/qualification/anthropic-native-final-proof.json`.
Dieser Nachweis betrifft denselben begrenzten Python-Auftrag ueber einen zweiten
Modellanbieter und erweitert nicht die unten genannten Aussagegrenzen.

Im Root der Vorlage:

```powershell
& .\Start-Coding-Agent.ps1 -Workspace "C:\Pfad\zum\projekt-worktree" `
  -Task "Beschreibe hier die konkrete Aenderung und ihre Abnahmekriterien."
```

Der Auftrag wird editierbar in AI Studio angezeigt. Starte ihn dort und pruefe
die vorgeschlagenen Schreib-/Testaktionen. Ein Git-Worktree mit bekanntem
Ausgangsstand ermoeglicht dem Reviewer eine nachvollziehbare Diff-Pruefung.

## Aussagegrenzen

Die Live-Abnahmen belegen konkrete Python-Auftraege und die Freigabe-/Review-Kette.
Der aktuelle hostseitige Testadapter fuehrt pytest aus; unittest-Testklassen werden
dadurch ebenfalls unterstuetzt. Andere Build-/Testwerkzeuge sind damit nicht live
abgenommen. Freigaben gelten fuer konkrete Aktionen; die Tests verleihen dem Agenten
keine allgemeine Berechtigung fuer Deployments oder externe Veroeffentlichungen.
Ein gruenes Review ist keine Garantie fuer beliebige zukuenftige Aufgaben.
