# Ideenspeicher

**Stand:** 2026-08-01
**Leitplanke:** Der aktuelle KMU-Controlling-Pilot bleibt P0.

## Zweck und Regeln

Dieser Speicher hält externe Ansätze und diskutierte Möglichkeiten auffindbar.
Er ist **keine Roadmap**, keine Implementierungsfreigabe und keine Zusage für
Abhängigkeiten. Ideen ändern ihren Status nur nach einer expliziten Diskussion;
bis dahin bleibt der dokumentierte Entscheidungsstand maßgeblich.

## Status

- **Nicht übernehmen:** bewusst kein Einsatz bzw. keine Installation.
- **Später prüfen:** nur bei dem unten genannten Auslöser erneut bewerten.
- **Strategischer Kandidat:** nach einem kontrollierenden Pilot konkretisieren.
- **Selektiv anwenden:** Prinzipien in eigener Form nutzen, ohne Fremdcode oder
  externe Laufzeitabhängigkeit.
- **Beobachten:** Erkenntnisse verfolgen, ohne Produktentscheidung.

## Übersicht

| Ansatz | Status | Aktuelle Entscheidung |
| --- | --- | --- |
| [Keep the Why](https://github.com/oliver-zehentleitner/keep-the-why) | Nicht übernehmen | Nur ADR-Begründungen aus Diskussionen nutzen. |
| [iFixAi](https://github.com/ifixai-ai/iFixAi) | Später prüfen | Keine Produktabhängigkeit. |
| [OpenWorker](https://github.com/andrewyng/openworker) | Strategischer Kandidat | Möglicher „AIStudio Edge Worker“ nach Pilot. |
| [Cindy](https://github.com/makecindy/cindy) | Beobachten | Kein Fork. |
| [AgentENV](https://github.com/kvcache-ai/AgentENV) | Später prüfen | Keine heutige Produktabhängigkeit. |
| [Harness Engineering](https://github.com/lopopolo/harness-engineering) | Selektiv anwenden | Read-only-Referenz, kein Fork. |
| [Thinking Orbs](https://github.com/Jakubantalik/thinking-orbs) | Später prüfen | UI-Politur erst im React-Frontend. |

## Einträge

### Keep the Why

- **Aktuelle Entscheidung:** Nicht installieren. Stattdessen die diskutierten
  Begründungen direkt in ADRs festhalten.
- **Nützliche Ideen:** Das „Warum“ von Entscheidungen dauerhaft nachvollziehbar
  machen.
- **Nicht übernehmen:** Keine zusätzliche Installation oder separates Tooling.
- **Kosten/Risiken:** Zusätzliche Pflegefläche ohne klaren Mehrwert gegenüber
  ADRs.
- **Erneut prüfen, wenn:** ADRs die Entscheidungsbegründungen nicht mehr
  ausreichend auffindbar oder nutzbar halten.

### iFixAi

- **Aktuelle Entscheidung:** Keine Produktabhängigkeit.
- **Nützliche Ideen:** Ein isolierter Audit für einen Azure-Agent-Release könnte
  später sinnvoll sein; dabei nur synthetische Daten, Telemetrie aus und ein
  hartes Budget.
- **Nicht übernehmen:** Keine Einbindung als Produktabhängigkeit.
- **Kosten/Risiken:** Budget- und Betriebsrisiko; daher Isolation, synthetische
  Daten und deaktivierte Telemetrie als Mindestbedingungen.
- **Erneut prüfen, wenn:** Nach dem P0-Piloten ein konkreter Azure-Agent-Release
  eine zusätzliche Audit-Prüfung benötigt.

### OpenWorker

- **Aktuelle Entscheidung:** Strategischer Kandidat für einen „AIStudio Edge
  Worker“, erst nach einem kontrollierenden Pilot.
- **Nützliche Ideen:** Lokale Imports und Connectoren, Zeitpläne,
  Freigabe-Inbox sowie Secret-Verwaltung.
- **Nicht übernehmen:** Keinen allgemeinen Coworker forken.
- **Kosten/Risiken:** Breiter Coworker-Umfang würde Fokus und Steuerbarkeit des
  KMU-Controlling-Piloten gefährden.
- **Erneut prüfen, wenn:** Der kontrollierende Pilot abgeschlossen ist und die
  genannten Fähigkeiten als konkrete, priorisierte Lücke bestätigt sind.

### Cindy

- **Aktuelle Entscheidung:** Beobachten; kein Fork.
- **Nützliche Ideen:** Mobile Freigaben und Fernsteuerung,
  harness-/modellunabhängiger Workspace mit Memory sowie
  modellübergreifendes Planen, Ausführen und Reviewen.
- **Nicht übernehmen:** Nicht forken: Das öffentliche Repository ist nur der
  Client, das Backend ist separat; zudem bestehen Standard-Cloud-Dienste,
  Analytics sowie hohe Desktop-/Mobile-Komplexität.
- **Kosten/Risiken:** Zusätzliche Backend-Abhängigkeit, Cloud- und
  Analytics-Vorgaben sowie hoher Plattformumfang.
- **Erneut prüfen, wenn:** Nach P0 ein klarer Bedarf für mobile Freigaben oder
  Fernsteuerung besteht und die Architektur- sowie Datenschutzfolgen separat
  bewertet wurden.

### AgentENV

- **Aktuelle Entscheidung:** Später prüfen; heute weder installieren noch in die
  Produktarchitektur aufnehmen.
- **Nützliche Ideen:** Isolierte Agenten-Ausführung, schnelles Pausieren und
  Fortsetzen per Snapshot, parallele Tests per Fork sowie eine
  E2B-kompatible Ausführungsschnittstelle.
- **Nicht übernehmen:** Keine eigene Firecracker-/KVM-Plattform für den
  KMU-Controlling-Piloten aufbauen.
- **Kosten/Risiken:** Linux-/KVM-Cluster, Snapshot-Speicher und laufender Betrieb;
  AgentENV enthält derzeit keine Autorisierung und darf daher nicht offen ins
  Internet gestellt werden.
- **Erneut prüfen, wenn:** Wir nicht vertrauenswürdigen Code ausführen oder
  hunderte isolierte Agentenumgebungen parallel betreiben müssen und einfachere
  Azure-Isolation nachweislich nicht mehr ausreicht.

### Harness Engineering

- **Aktuelle Entscheidung:** Als Read-only-Methodenreferenz selektiv anwenden;
  keine Installation, Laufzeitabhängigkeit oder Fork.
- **Nützliche Ideen:** Kurzer Agentenvertrag mit Ziel, Datenquellen, erlaubten
  Aktionen, Freigaben, Belegen und Tests; Kontext nur bei Bedarf laden; Tools
  maschinenlesbar beschreiben; Korrekturen in geprüfte Regeln oder Tests
  überführen.
- **Nicht übernehmen:** Keine fremde Repository-Struktur, Playbooks oder Texte
  in Produkt und Kundenunterlagen kopieren.
- **Kosten/Risiken:** Zu viele Regeln erhöhen Pflege- und Kontextkosten.
  Repository-eigene Inhalte stehen unter CC BY 4.0; Quellmaterial kann anderen
  Rechten unterliegen. Vor jeder Übernahme `COPYING.md` prüfen und übernommene
  oder bearbeitete CC-BY-Inhalte korrekt attribuieren.
- **Nächster Prüfpunkt:** Vor dem nächsten Agententyp einen repräsentativen Job
  einmal als Baseline ausführen, nur die früheste belegte Lücke schließen und
  frisch wiederholen. Im generischen Kern zuerst strukturierte Evidence Records,
  Tool Contracts und native Abnahmetests je Agentenpaket bewerten.

### Thinking Orbs

- **Aktuelle Entscheidung:** Nicht in den heutigen HTML-/JavaScript-Prototyp
  einbauen; als UI-Kandidat für ein späteres React-Frontend vormerken.
- **Nützliche Ideen:** Sechs klar unterscheidbare Agentenzustände, automatische
  Hell-/Dunkel-Anpassung, reduzierte Bewegung und ressourcenschonendes Pausieren
  außerhalb des sichtbaren Bereichs.
- **Nicht übernehmen:** Kein React nur für eine kosmetische Ladeanimation
  einführen und keine Aktivität vortäuschen, die das Backend nicht meldet.
- **Kosten/Risiken:** MIT-lizenziert und ohne API-Kosten; zusätzlicher
  Frontend-Pflegeaufwand sowie Ablenkung bei zu häufigem Einsatz.
- **Erneut prüfen, wenn:** Das Produktions-Frontend React nutzt und ein
  Usability-Test zeigt, dass Nutzer bei realen Wartephasen den Agentenstatus
  nicht verstehen. Dann zuerst genau einen echten Statuspfad testen.
