# Dynamischer Wachstumsworkflow

Der Ablauf ist beobachtungsgetrieben und wird nach jedem Ergebnis neu entschieden:

1. **Observe:** Prozesszustand, letzte abgeschlossene Session, verifizierte eigene 24h-/7d-
   Outcomes, Followerstand und Messqualitaet lesen.
2. **Diagnose:** Messfehler, Distributionsproblem, Themenproblem, Hookproblem und technische
   Stoerung auseinanderhalten.
3. **Choose:** genau eine reversible Hypothese mit der hoechsten erwarteten Lernwirkung waehlen.
4. **Prepare:** je nach Luecke recherchieren, kleine Kandidatenmenge entwerfen oder eine
   technische Korrektur vorschlagen.
5. **Verify:** der separate read-only Verifier prueft Evidenz, Stimme, Duplikate, Schutzgates,
   Messplan und unerwuenschte Nebenwirkungen.
6. **Execute boundary:** Der Operator formuliert hoechstens eine konkrete Aktion. Es gibt in
   diesem Agentenpaket keine direkte Live-X-Ausfuehrung; die bestehende Marketingbot-Pipeline
   bleibt der einzige Live-Verbraucher.
7. **Measure:** Ergebnis erst nach dem definierten Messfenster mit eigener Statusidentitaet
   bewerten. Danach beibehalten, reparieren oder zuruecknehmen.

Der Lauf stoppt bei fehlenden frischen Daten, krankem Runtime-Zustand, unklarer
Aktionsidentitaet, ausstehendem Review, erschoepftem Budget oder erreichtem Messplan.
