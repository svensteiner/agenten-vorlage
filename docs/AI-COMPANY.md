# Einordnung in dein AI-Company-Projekt

Untersucht am 16.09.2026: `C:\Users\botrunner\projects\AI-Company`.
Das Projekt wurde nur gelesen. Vorhandene uncommittete Änderungen wurden nicht angefasst.

## Was bereits vorhanden ist

| Fundstelle | Beobachtung | Konsequenz für diese Vorlage |
|---|---|---|
| `AGENTS.md` | Paperclip-Control-Plane, Company-Grenzen, atomarer Checkout | Paperclip als Auftrags-Owner erhalten |
| `agent-vorlage/agent.py` | Observe/Think/Act/Reflect und lokaler Scheduler | Gemeinsame kleine Laufzeit statt Kopien |
| `agent-vorlage/skill_loader.py` | Lädt `skill.py` dynamisch; `load_all()` lädt alle Pakete | Portable SKILL.md-Anweisungen getrennt von ausführbaren Tools |
| `agents/create_agent.py` | Kopiert `_template`, ersetzt Platzhalter in SOUL und Heartbeat | Rollen/Skills konfigurieren statt Code kopieren |
| `agents/_template/heartbeat.py` | Schlüsselwort-Fallback und feste `SCRIPTS`-Zuordnung | Nächsten Schritt anhand des Ergebnisses auswählen |
| `agents/agent_registry.json` | Rollen und Startbefehle für Company-Agenten | Kein zweites konkurrierendes Company-Register erzeugen |
| `agents/paperclip_sdk.py` | Company/Agent-Bindung, Checkout, Run-ID und Task-Updates | Bestehenden Client weiterverwenden |
| `companies/ai-studioxyz/COMPANY.md` | Agentcompanies-Paket und asynchrone Zusammenarbeit | Pakete portabel halten, Company-Bus nicht ersetzen |
| `companies/ai-studioxyz/agents/cto/AGENTS.md` | Sven-gesteuertes Go-live und Artefakt-Smoke | Lokale Fertigstellung nicht als Deployment melden |
| `doc/plans/2026-04-23-agent-template-audit.md` | Historischer Audit beschreibt Drift zwischen Agenten | Als Kontext, nicht als aktueller Vollständigkeitsnachweis behandeln |

Die lokalen `packages/adapters/codex-local/index.js` enthalten lediglich `// stub`.
Deshalb wurde daraus keine funktionierende Adapterintegration abgeleitet. Die wirklich vorhandene
Codex-CLI wurde über ihre Hilfe geprüft. Dieses Audit ist auf relevante Vorlagendateien begrenzt.

## Empfohlene Rollen-Zuordnung

| Company-Rolle | AgentKit-Profil | Ergänzung |
|---|---|---|
| CTO | developer | Website-/Deploy-Wissen als zusätzliche Skills; Go-live separat |
| CMO | marketing | Produktfakten, Markenstimme und Kanalregeln |
| CSO | sales | Qualifizierung, CRM-Regeln und autorisierte Outreach-Grenzen |
| CSM | support | Produktwissen, Supportregeln und Eskalationen |
| CPO | company oder eigene product-Konfiguration | Product-Skill und reduzierte benötigte Rollen |
| SEO | research plus eigene SEO-Rolle | Search-Console-Zugriff als Host-Tool, SEO-Verfahren als Skill |
| CEO | company | Koordinator, nicht neuer Ersatz für Focus-Engine und Registry |
| Steuerberatung/BMD | bmd-tax-advisor | BMD-Adapter und Mandatsdaten separat freigeben; `tax-reviewer` als Vier-Augen-Gate |

Für einen ersten Pilot den CTO auf einem isolierten Checkout nutzen. Danach die vorhandenen
CMO/CSO/CSM-Spezialisierungen schrittweise auf gemeinsame Skills umstellen. Nicht alle laufenden
Heartbeats gleichzeitig migrieren.

## Integrationsvertrag — vorbereitet, nicht live verdrahtet

`agentkit/integrations.py` enthält getestete, netzwerkfreie Übersetzungsfunktionen:

```python
from agentkit.integrations import issue_to_task, result_to_update

# client ist euer bereits konfigurierter PaperclipClient.
issue = client.get_task(issue_id)
task = issue_to_task(issue, company_id=client.company_id, agent_id=client.agent_id)

# Nur in einem autorisierten Heartbeat einbinden, nicht als zweiter Poller starten:
if client.checkout(issue_id):
    state = engine.run(task)
    update = result_to_update(state)
    client.update_task(issue_id, status=update["status"], comment=update["comment"])
```

Der Code ist eine Einbauanleitung, kein bereits ausgeführter Aufruf. Vor Produktivbetrieb:
den existierenden Heartbeat-Lifecycle verwenden, gültige Run-ID aus der Orchestrierung erhalten,
Checkout-409 ohne Arbeit beenden und Updates gegen die installierte Serverversion prüfen.
Ergebnisberichte lokal speichern, damit ein fehlgeschlagenes API-Update **nicht** den Worker erneut
startet. `result_to_update` liefert keinen eigenständigen Idempotenzschutz für das Control Plane.
Wenn der Heartbeat bereits einen Task ausgecheckt hat, dessen vorhandenen Lifecycle nutzen;
das obige Checkout nicht doppelt ausführen.

Company-Namen in `agent.json` sind lokale Labels. Paperclip-Grenzen verwenden UUIDs und werden
gegen den Client geprüft. Display-Namen sind keine API-Authentifizierung. Beim Resume zusätzlich
immer dieselbe externe Issue-ID und Company-Bindung im aufrufenden Heartbeat beibehalten.

Der BMD-Agent liegt als portables Paket unter `agents/bmd-tax-advisor`. Er ist für die
Einbindung in einen Paperclip-Agenten vorbereitet, führt aber ohne euren konkret freigegebenen
BMD-Adapter keine Buchung oder Übermittlung aus. Mandatsdaten sollten in einem separaten,
zugriffsbeschränkten Checkout/Workspace bleiben; die AgentKit-Vorlage enthält nur redigierte
Arbeits- und Lernstrukturen.

Geldbudgets und Kostenberichte gehören weiter in Paperclip. Der lokale Runner kennt nur
Zeit, Schritte, Fehler und Kontextgröße. Ein nativer DSH-Lauf braucht zusätzlich die Übernahme
von Ergebnis-, Abbruch- und Kosteninformationen durch einen späteren Bridge-Adapter.
