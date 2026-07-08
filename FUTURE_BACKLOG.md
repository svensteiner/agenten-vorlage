# FUTURE_BACKLOG — nach der Demo (Phase 2+)

> Ideen, die **außerhalb** der aktuellen Prototyp-Mission liegen. Hier geparkt, damit
> der Fokus auf der Kundendemonstration bleibt. **Nicht in Phase 1 bearbeiten.**

## Enterprise-Datenplattform (Phase 2)
- Echte Konnektoren zu SharePoint, SAP, Fileserver, Exchange (Ingestion-Pipeline).
- Echtes RAG: Embeddings, Vektor-Index, hybride Retrieval-Pipeline.
- **Semantische globale Suche:** Die Command-Palette (Zyklus 17) filtert clientseitig über Titel/Typ/
  Snippet/Autor. Phase 2 könnte sie an echte Volltext-/Vektor-Suche über die angebundenen Systeme
  anbinden (der `matchDocs()`/`renderSearchResults()`-Pfad ist der vorgesehene UI-Andockpunkt).
- **Echte Provenance-/Lineage-Graphen:** Die Demo inszeniert die Entscheidungskette (Zyklus 14,
  `answer.chain`) noch handkuratiert. Phase 2 könnte die Kette **automatisch** aus Dokument-Metadaten
  (E-Mail-Threads, Referenzen, Zeitstempel) rekonstruieren — das `answer.chain`-Feld ist der
  vorgesehene UI-Andockpunkt.
- **Compliance-/DSGVO-Automatisierung:** Das Datenschutz-Szenario (Zyklus 16) zeigt Audit-Status und
  Verzeichnis von Verarbeitungstätigkeiten noch handkuratiert. Phase 2 könnte VVT-Einträge und offene
  Auflagen **automatisch** aus den angebundenen Systemen ableiten und Fristen aktiv überwachen (der
  Status-Tabellen-Renderer ist der vorgesehene UI-Andockpunkt).
- Permission-faithful Retrieval gegen echte ACLs. *(Die Demo visualisiert dieses Versprechen
  bereits in Zyklus 7 — gesperrte Dokumente + „N weitere Treffer für Sie nicht freigegeben".
  Phase 2 muss das UI nur an echte Berechtigungs-Checks anbinden; das `withheld`-Feld pro
  Antwort und das `locked`-Flag pro Dokument sind die vorgesehenen Andockpunkte.)*
- **Hinweis:** Für viele dieser Themen existiert bereits ausgearbeitete Architektur-
  Dokumentation unter [`platform/`](platform/) (31 Zyklen Vorarbeit). Diese ist das
  technische Fundament für Phase 2 — in Phase 1 aber **eingefroren/nicht anfassen**.

## Agent-Framework (Phase 2)
- Orchestrator/Planner/Verifier aus [`core/`](core/) an echte Modelle anbinden.
- Multi-Agent-Workflows, Tool-Scope, Handoffs (in `platform/orchestration/` bereits spezifiziert).

## Skill-Bibliothek (Phase 3)
- Domänen-Packs (Finance/HR/Legal/Audit/…) — in `platform/packs/` bereits als Specs vorhanden.

## Produktreife
- Authentifizierung/SSO, Mandantenfähigkeit, Audit-Log, Kosten-Governance.
- Deployment, DR, regionale Topologie (in `platform/deployment/` spezifiziert).
- Performance-Optimierung, Skalierung, Monitoring/SLOs.

---

### Warum das hier liegt
Die Mission (Phase 1) ist **ausschließlich** der Kunden-Demo-Prototyp. Sobald die
Demonstration abgenommen ist, wird das Projekt mit Enterprise-Datenplattform,
Agent-Framework und Skill-Bibliothek fortgesetzt — dann wird `platform/` vom
eingefrorenen IP zum aktiven Bauplan.
