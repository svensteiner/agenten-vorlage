# Austauschbare Modell-APIs

Rollen, Skills, Workspace, Freigaben und Review bleiben gleich. Fuer die Ausfuehrung
stehen `codex`, `deepseek` und lokal `api` sowie `anthropic` zur Wahl. `api` nutzt eine frei konfigurierte
Chat-Completions-Schnittstelle; ein OpenAI-Konto ist dafuer nicht erforderlich.

## Konfiguration

Setze diese Variablen in der Umgebung des AgentKit-/AI-Studio-Prozesses:

- `AGENTKIT_API_BASE_URL`: HTTPS-Basisadresse inklusive API-Praefix, ohne
  `/chat/completions`, eingebettete Zugangsdaten, Query oder Fragment.
- `AGENTKIT_API_KEY`: Schluessel des gewaehlten Anbieters; nicht in Git speichern.
- `AGENTKIT_API_MODEL`: Modellkennung des Anbieters.
- Optional `AGENTKIT_API_JSON_MODE=off`: fuer Modelle ohne `json_object`-Unterstuetzung.
  Der Agent verlangt weiterhin strukturierte JSON-Antworten und validiert sie.

Die Konfiguration muss vor dem Serverstart vorhanden sein. Ein schon laufender
Server uebernimmt keine spaeteren Variablen aus einer anderen PowerShell-Sitzung.
Schluessel werden weder ueber CLI-Argumente noch ueber die Browserkonfiguration ausgegeben.
Die bisherige DeepSeek-Schluesselverwaltung bleibt separat.

```powershell
# Basisadresse und Modell gemaess der Dokumentation deines Anbieters waehlen.
$env:AGENTKIT_API_BASE_URL = "https://openrouter.ai/api/v1"
$env:AGENTKIT_API_MODEL = "<Modellkennung>"
# AGENTKIT_API_KEY in der Prozessumgebung setzen, nicht als Programmargument.
& .\Start-Coding-Agent.ps1 -Backend api -Workspace "C:\Pfad\zum\projekt-worktree" `
  -Task "Behebe den beschriebenen Fehler und pruefe Code und Tests."
```

CLI:

```powershell
python -m agentkit run --backend api --agent agents\programming-agent `
  --workspace "C:\Pfad\zum\projekt-worktree" --task "Dein konkreter Auftrag"
```

In AI Studio erscheint **Eigene Modell-API**. Sie wird erst bei vollstaendiger,
gueltiger Serverkonfiguration waehlbar. Das Modellfeld kann die konfigurierte
Modellkennung fuer einen neuen Auftrag ueberschreiben. Ein Endpointwechsel kann
keinen offenen Checkpoint oder eine ausstehende Aktion des bisherigen Providers uebernehmen.

## Anbieter und Protokolle

- [OpenRouter Chat Completions](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request?explorer=true)
  verwendet `https://openrouter.ai/api/v1` und die dort angebotenen Modellkennungen.
- [Google Gemini: kompatible Schnittstelle](https://ai.google.dev/gemini-api/docs/openai)
  verwendet `https://generativelanguage.googleapis.com/v1beta/openai` und Gemini-Zugangsdaten.
- DeepSeek und andere gehostete Chat-Completions-Anbieter koennen mit ihrer jeweiligen
  HTTPS-Basisadresse und Modellkennung verwendet werden.

Kompatibles Protokoll bedeutet kein Zugriff auf OpenAI: Schluessel und Modellanfragen
gehen ausschliesslich an die konfigurierte Adresse. Gemini-spezifische Zusatzfunktionen,
Azure-Sonderauthentifizierung und unverschluesselte
lokale HTTP-Endpunkte werden von diesem Adapter nicht angeboten.

## Native Anthropic Messages

`anthropic` verwendet ausschliesslich `https://api.anthropic.com/v1/messages`.
Standardmodell ist `claude-haiku-4-5-20251001`; `ANTHROPIC_MODEL` oder das Modellfeld
koennen die Modellkennung ersetzen. Den Schluessel in den lokalen Provider-Einstellungen
unter Anthropic hinterlegen oder `ANTHROPIC_API_KEY` in der Prozessumgebung setzen.
Die lokale Schluesselablage ist unter Windows mit CurrentUser-DPAPI geschuetzt.
Transportfehler wechseln nicht still zu einem anderen Anbieter. Freigaben, Workspace-
Grenzen, Testnachweise und separates Review gelten weiterhin.

```powershell
& .\Start-Coding-Agent.ps1 -Backend anthropic -Workspace "C:\Pfad\zum\projekt-worktree"
```

## Gepruefte Grenzen

Transport-, Tool-, JSON-Modus-, Konfigurations- und Checkpoint-Vertraege werden mit
Fixtures geprueft. Der vorhandene reale Codex-Nachweis ist kein Live-Nachweis fuer
weitere Anbieter. Ein API-Modell muss strukturierte Antworten und Function Calling
fuer die angebotenen Werkzeuge unterstuetzen; konkreter Modellzugriff ist erst nach
einem erfolgreichen Auftrag bestaetigt. Kosten entstehen beim gewaehlten Anbieter.
Eigene API-Endpunkte sind nur im lokalen Modus freigeschaltet.

Am 12.10.2026 bestand ein echter nativer Anthropic-Lauf mit Haiku 4.5:
`dd23c252e06347fc9879c3fb34cd7aee`. In einem isolierten Git-Projekt wurde nur
`app.py` geaendert, ein unveraenderter Test bestand und eine separate read-only
Rolle bestaetigte Diff und Testnachweis. `STATUS.md` und Testdatei blieben
unveraendert. Lokaler Nachweis: `.runs/qualification/anthropic-native-final-proof.json`.
Dies belegt diesen begrenzten Auftrag, nicht die Zuverlaessigkeit beliebiger Aufgaben.
