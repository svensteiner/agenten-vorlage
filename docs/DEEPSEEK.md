# DeepSeek Harness als Ausführungshost

**Empfehlung:** Die Rolle von DeepSeek Harness ist die austauschbare Ausführungsschicht.
Paperclip behält Company-Aufgaben und Zuständigkeiten. AgentKit liefert portable Rollen/Skills
und eine kleine separat testbare Referenzschleife. Keine drei konkurrierenden Scheduler starten.

Die [offizielle Einführung](https://www.deepseek.com/harness/en/) beschreibt einen Cordis-basierten
Pluginansatz. Das passt zur gewünschten Austauschbarkeit. Die native Trajectory ist für die
Untersuchung tatsächlicher Werkzeugaufrufe nützlicher als nur ein abschließender Agentenbericht.
Die Architektur bleibt Developer Preview; keine Produktionsstabilität daraus ableiten.

## Was diese Vorlage konkret unterstützt

- Alle erzeugten Skills liegen als `<name>/SKILL.md` in `.agents/skills`.
- `native-prompt` erzeugt einen auf das Agentenpaket bezogenen Auftrag mit Rollen-/Skill-Katalog.
- Der dynamische Workflow steht als eigenes Skill bereit, das der native Harness laden kann.
- Rollen und Skills enthalten keine Abhängigkeit vom Codex-Adapter oder einem bestimmten Modell.

Es gibt **keinen** behaupteten fertigen Cordis-Pluginadapter und keinen automatisch registrierten
DSH-Prozess. Native DSH-Ausführung und Python-Engine sind alternative Laufwege. Deren Checkpoints
sind nicht gegenseitig resumierbar. AgentKit-Schemas/Locks/Limits wirken nur im Python-Runner.

## Direkter DeepSeek-API-Pilot

Für einen schnellen Coding-Agent-Test gibt es zusätzlich den Backend-Wert `deepseek`. Er nutzt
DeepSeeks OpenAI-kompatiblen Chat-Completions-Endpunkt und JSON Output; die Engine validiert die
Antwort danach nochmals gegen ihre eigenen Decision-/Report-Schemas. Der API-Key bleibt nur in
der lokalen Umgebungsvariable und wird nie in `agent.json`, Statusdateien oder Logs geschrieben.

```powershell
$env:DEEPSEEK_API_KEY = "<lokal setzen, nicht committen>"
$env:DEEPSEEK_MODEL = "deepseek-chat"

python -m agentkit run `
  --agent agents\programming-agent `
  --backend deepseek `
  --workspace C:\Users\botrunner\projects\deepseek-coding-sandbox `
  --task "Erstelle eine kleine Python-Funktion zur Normalisierung von Telefonnummern mit Tests."
```

Der Workspace sollte ein separater Test- oder Git-Worktree sein. Erst einen kleinen, reversiblen
Auftrag verwenden und die erzeugten Artefakte sowie `.runs/<run-id>/state.json` prüfen. Ein echter
API-Smoke-Test wurde bereits in einer isolierten Sandbox ausgeführt; der Schlüssel wurde nicht
persistiert. Für weitere Läufe muss `DEEPSEEK_API_KEY` lokal konfiguriert sein.

## Start mit Weboberfläche

Erst ein Paket erzeugen, zum Beispiel `generated\company` mit Profil `company`.
Danach in dessen Verzeichnis:

```powershell
Set-Location generated\company
git init
npx @deepseek-ai/dsh web --no-open
```

Die Initialisierung eines eigenen Git-Roots macht die Skill-Suche eindeutig, auch wenn das
Paket in diesem Repository liegt. Bei einem externen Verzeichnis ohne übergeordnetes Git-Repo
ist sie nicht zwingend nötig. Im Harness Modell/Zugang konfigurieren, dieses Agentenverzeichnis
als Workspace auswählen und den mit `native-prompt` erzeugten Auftrag verwenden.
Abhängigkeiten werden beim ersten `npx`-Start heruntergeladen. Für einen reproduzierbaren Pilot
eine geprüfte veröffentlichte Version statt dauerhaft `latest` pinnen.

Der Skill-Provider bestimmt den Projektroot anhand des nächsten `.git`-Vorfahren und unterstützt
`.agents/skills` sowie explizite zusätzliche Skill-Verzeichnisse. Das Verzeichnis `workspace/`
enthält die eigentlichen Arbeitsergebnisse. [Quelle: Skill-Provider](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md).

## Headless nach der Konfiguration

Aus dem Projektroot dieser Vorlage den Aufgabenprompt erzeugen:

```powershell
.\.venv\Scripts\python.exe -m agentkit native-prompt --agent generated\company --task "Erstelle einen kleinen getesteten Prototyp im workspace-Verzeichnis." | Set-Content -Encoding utf8 generated\company\TASK.md
Set-Location generated\company
Get-Content -Raw TASK.md | npx @deepseek-ai/dsh --profile headless
```

Der dokumentierte Headless-Modus nimmt den Auftrag auch über stdin an. Optional bietet er
einen JSON-Eventstrom und Session-Fortsetzung. Bei einer späteren automatischen Bridge den
Exitcode prüfen, nicht nur das Vorhandensein eines `final`-Events. [Quelle: Headless-Vertrag](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/bundle/headless/README.md).

Dieser Startweg wurde gegen den Upstream-Quellcode geprüft, nicht live ausgeführt. Prüfe vor
dem Pilot die installierte CLI-Hilfe und setze Berechtigungen/Budgets in DSH. Eine Aufforderung
im Prompt ersetzt keine technisch durchgesetzte Berechtigung.

## Ausbau ohne Doppelarbeit

1. Ein Entwickler-Paket mit wenigen Skills nativ ausführen und Artefakte/Trajectory prüfen.
2. Company-Rollen als native Presets abbilden; gemeinsame Fähigkeiten als Plugins konfigurieren.
3. Erst dann einen schmalen Paperclip-Adapter ergänzen: Issue-Checkout → native Session →
   überprüftes Ergebnis → Status/Kosten zurückmelden. Gleiche Company- und Owner-Bindung erhalten.
4. Ein nativer Plugin-Adapter braucht Integrationstests für Abbruch, Rückgabeformat, Wiederaufnahme
   und Berechtigungen. Nicht allein aus einem erfolgreichen Start als fertig betrachten.

