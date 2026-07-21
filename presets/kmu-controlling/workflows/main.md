# KMU-Controlling-Workflow

## Stündlicher adaptiver Lauf

1. Prüfe neue oder geänderte Dateien anhand der konfigurierten Input-Globs.
2. Validiere Struktur, Zeitraum, Vorzeichen und Konten-Mapping.
3. Bei fehlenden Pflichtdaten: Profil `missing_data` aus `pilot/prompt-profiles.json` wählen und die betroffene Berechnung stoppen.
4. Berechne Kennzahlen und Abweichungen ausschließlich deterministisch.
5. Vergleiche mit dem letzten geprüften Stand und priorisiere nur materielle Veränderungen.
6. Erstelle einen klaren Entwurf mit Fakten, Risiken, Maßnahmen und offenen Fragen.
7. Bei einer externen Aktion: Entwurf als Freigabe vorlegen und warten.

## Fehler und Leerlauf

Bei Datenfehlern keine Schätzung vornehmen. Nach der konfigurierten Anzahl aufeinanderfolgender Fehler eskalieren. Ohne neue Eingaben den Status dokumentieren und bis zum nächsten Lauf warten.
