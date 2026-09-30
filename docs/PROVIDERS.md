# Lokale Provider-Einstellungen

Unter `/settings` kann der Besitzer einen DeepSeek-API-Schlüssel speichern oder
den gespeicherten Schlüssel entfernen. Speichern prüft Format und lokale Speicherung,
führt aber keinen Modellaufruf aus. Ein eingerichteter Anbieter ist noch kein Nachweis
für gültige Zugangsdaten, Guthaben oder erfolgreiche Modellaufgaben.

Die Speicherung verwendet Windows DPAPI im CurrentUser-Kontext. Die verschlüsselte
Datei liegt unter `cockpit/.runs/providers/deepseek.json`; Klartext wird nicht auf
Datenträger geschrieben. Die Entschlüsselung benötigt das passende Windows-Benutzerprofil.
Ein Backup dieser Datei allein ist deshalb kein portabler Export des Schlüssels.
Andere Prozesse desselben Windows-Benutzers sind keine Sicherheitsgrenze von DPAPI.

Ein gespeicherter Schlüssel hat Vorrang vor `DEEPSEEK_API_KEY`. Entfernen löscht nur
den gespeicherten Wert; eine gesetzte Umgebungsvariable bleibt nutzbar. Ein beschädigter
Speicher wird als Fehler angezeigt, ohne still auf einen anderen Schlüssel zu wechseln.
Außerhalb von Windows bleibt die Umgebungsvariable nutzbar; persistentes Speichern
ist dort nicht verfügbar.

Die Oberfläche verwendet ein Passwortfeld und leert es nach dem Speicherversuch.
Schlüssel werden weder als Browser-Draft noch in Job-Metadaten gespeichert oder durch
die Status-API zurückgegeben. Der lokale Server übergibt sie direkt an den Backendadapter.
Das Cockpit verwendet dafür ausschließlich `https://api.deepseek.com`; eine abweichende
`DEEPSEEK_BASE_URL` gilt dort nicht. Bereits gestartete Jobs behalten ihren Schlüssel;
neu gestartete oder wiederaufgenommene Jobs lesen die aktuelle Einstellung.

Die Seite und API sind durch dieselben Loopback-, Host-, Origin- und CSP-Regeln wie
das übrige Cockpit geschützt. Das Produkt bleibt für einen lokalen Besitzer ausgelegt.
Provider-Einrichtung erweitert keine Werkzeugrechte: DeepSeek-Dateiänderungen und
Testaufrufe benötigen weiterhin konkrete Aktionsfreigaben.

## Prüfungen

Speicherprüfungen verwenden ausschließlich synthetische Schlüssel in temporären
Verzeichnissen. HTTP-Verträge prüfen Herkunftsschutz, Fehler ohne Geheimnisinhalt,
Backend-Injektion und unveränderte Job-Persistenz. Diese Prüfungen ersetzen keine
Live-Modellabnahme.

Am 30.09.2026 bestanden 123 Unittests, Ruff und 16 Offline-Release-Prüfungen.
Die Browser-Abnahme nutzte einen getrennten lokalen Testserver mit synthetischem
Schlüssel: Speichern, geleertes Passwortfeld, Reload und Entfernen erfolgreich.
Ein separater Python-Prozess bestätigte die native DPAPI-Entschlüsselung nach dem
Browser-Speichern und das Fehlen des Klartextwerts in der gespeicherten Datei.
Automatisiert geprüft wurden außerdem manipulierte Ciphertexte, fehlende
Speicherberechtigung, nicht verfügbare Verschlüsselung und Erhalt des bisherigen
Werts bei fehlgeschlagener Verschlüsselung. Keine echten Zugangsdaten und keine
kostenpflichtigen Modellaufrufe wurden dafür verwendet.
