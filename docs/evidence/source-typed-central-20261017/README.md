# Strukturierter zentraler API-Kandidat: Unit-Regression

Der isolierte Kandidat besteht den vollstaendigen tests/unit-Lauf:
4.641 bestanden, elf Skips, fuenf erwartete Fehler, 42 Warnungen,
295,53 Sekunden, Exit 0. Zwoelf ueberwachte Quellen-/Testdateien bleiben
waehrend des Laufs bytegleich; vor/nach-Hashes und Rohlog sind beigefuegt.
Das ist der komplette Unit-Testordner, kein Browser-/Live-X-/Provider-End-to-End-Test.

Der vorherige Lauf bleibt erhalten: 4.640 bestanden, ein Fehler. Ein gemockter
Generator war noch als echter OpenAI-Transporterfolg erwartet worden. Nur diese
Assertion wurde auf unknown korrigiert und erklaert. Der Test prueft weiterhin,
dass Generierung alleine keinen veroeffentlichten Reply speichert. Separate
Review bestaetigt diese Korrektur; die 80 relevanten Nachtests bestanden.
Echte erfolgreiche Provider-/Fallback-Herkunft ist separat transportgemockt getestet.

## Umfang und Grenzen

Der Kandidat nutzt fuer die expliziten Quellreview-/Reparaturtasks geschlossene
JSON-Schemas auf Native-Anthropic und OpenRouter, dekodiert Reparaturen streng
und sperrt nicht unterstuetzte strukturierte Routen. Er korrigiert die
OpenRouter-only-Erreichbarkeit ohne OpenAI-Key, weist die tatsaechlich
beobachtete Erfolgsroute aus und entfernt OpenRouter-Fehlerbody-/Exceptiontexte
aus Logs. Gewoehnliche erfolgreiche Antworttexte bleiben teilweise geloggt.
Keine allgemeine Datenschutz- oder Providerabnahme.

**Nicht auf Marketingbot/master uebernommen und nicht aktiviert.**
Die echten v3/v4-Modellstudien verwendeten eigene Diagnoseadapter und beweisen
nicht diesen zentralen Produktionsweg. Ihre semantische Gegenpruefung fand
einen False-Accept. Ein gruener Unit-Lauf ersetzt weder dessen Reparatur noch
eine neue echte Inhaltsabnahme oder einen autonomen Coding-Projektabschluss.
[Modellstudien und Gegenbeweis](../source-faithfulness-typed-protocol-20261017/README.md).
