# Quellen und Auswahlentscheidung

Recherchiert am **16.09.2026**, anhand der Originalrepositories und offiziellen Dokumentation.
Die Auswahl richtet sich nach deinem Python/Paperclip-Bestand und portablen Skills, nicht nach
Sternzahlen. Die folgenden Einordnungen sind unsere Architekturentscheidung.

| Quelle | Übernahme | Bewusste Grenze |
|---|---|---|
| [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) | Plugin-/Host-Trennung, nativer Startweg, portable Skill-Verzeichnisse | Preview; kein ungeprüfter produktiver Adapter |
| [Agent Skills Specification](https://agentskills.io/specification) | SKILL.md, Name/Beschreibung, Ressourcen und bedarfsgerechtes Laden | Skills sind keine Toolrechte |
| [Anthropic Skills](https://github.com/anthropics/skills) | Referenz für interoperable Skill-Pakete | Keine pauschale Kopie aller Skills/Lizenzen |
| [Superpowers](https://github.com/obra/superpowers) | Ein konkretes Verification-Skill unverändert mit Lizenz übernommen | Keine erzwungene komplette Entwicklungspipeline |
| [Agency Agents](https://github.com/msitarzewski/agency-agents) | Inspiration für getrennte fachliche Rollen | Eigene knappe Rollen statt großer Personas und pauschaler Leistungsversprechen |
| [Paperclip Companies](https://github.com/paperclipai/companies) | Referenz für Company-Pakete und Teamstruktur | Kein Import fremder Companys in deinen laufenden Server |
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | Abgrenzung Koordinator/Spezialist und austauschbare Ausführung | Keine zusätzliche SDK-Abhängigkeit neben der vorhandenen Codex-CLI |

## Tatsächlich kopierte Upstream-Dateien

`agentkit/library/skills/verification-before-completion/` enthält das unveränderte Skill
aus `obra/superpowers` sowie dessen MIT-Lizenz. Der genaue Commit und SHA-256 stehen in
`UPSTREAM.json`; ein Test kontrolliert den Hash. Jedes erzeugte Paket mit diesem Skill
enthält auch Lizenz und Herkunft. Es gibt keine automatischen Updates von `main`.

Die übrigen Runtime-Dateien, Rollen und Skills sind eigens für diese Vorlage verfasst.
`debug-systematically` nutzt den allgemeinen Ansatz einer kausalen Fehlersuche, ohne die
umfangreichen Upstream-Prozessregeln oder die dortigen Abhängigkeiten zu kopieren.

## Warum nicht ein einziges riesiges Framework klonen?

Dein AI-Company-Projekt besitzt bereits Zuständigkeiten, Heartbeats und einen Control Plane.
Ein zweiter globaler Orchestrator würde neue Konflikte schaffen. Daher: portable Agentenpakete
und eine kleine austauschbare Ausführungsschnittstelle. Für umfangreiche native Werkzeuge und
Sessions DeepSeek Harness nutzen; Company-weite Auftragssteuerung in Paperclip belassen.

Das bedeutet auch: keine Behauptung, alle Vorlagen seien produktionsreif oder für jede Rolle
passend. Insbesondere sind ein guter Prompt, ein gestarteter Prozess und ein wirklich
verifiziertes Geschäftsergebnis unterschiedliche Nachweise.

