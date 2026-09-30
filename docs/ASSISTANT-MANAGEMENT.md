# Assistenten verwalten

## Vorgaben bearbeiten

`Vorgaben bearbeiten` öffnet die Beschreibung und Vorgaben des Assistenten aus
`SOUL.md`. Der vollständige Text ist bearbeitbar und bleibt Teil des portablen
Agentenpakets. Speichern akzeptiert nichtleeren UTF-8-Text bis 32.000 Bytes.
Die technische Identität, Company-Bindung, Profil, Rollen und Skills stammen weiter
aus der Agentenkonfiguration; der Texteditor ändert diese Einstellungen nicht.

Ein Auftrag speichert die gemeinsamen Vorgaben bei seinem Start. Laufende Aufträge,
Wiederaufnahmen und wartende Freigaben verwenden diese gespeicherte Fassung. Neue
Aufträge und spätere Nachrichten eines Dialogs verwenden die dann aktuelle Fassung.
Bereits gespeicherte Nachrichten und Ergebnisse werden nicht neu berechnet.

Eine ältere offene Ausführung ohne gespeicherte Vorgaben verhindert das Bearbeiten.
Sie muss zunächst kontrolliert wiederaufgenommen und abgeschlossen werden. Die
Anwendung erfindet keine rückwirkende Fassung für einen historischen Lauf.

Der Editor prüft beim Speichern die geladene Dateiversion. Hat eine andere Sitzung
die Vorgaben geändert, bleibt der Entwurf erhalten; die aktuelle Fassung muss
ausdrücklich neu geladen werden. Auch nach einer unklaren Netzwerkantwort wird
nicht automatisch erneut gespeichert. Ein identischer bereits gespeicherter Text
ist serverseitig idempotent. Die Datei wird atomar ersetzt; externe Editoren nehmen
allerdings nicht an der internen Prozesssperre teil.

## Archivieren und wiederherstellen

Unter `/assistants` lassen sich Assistenten aus der Auswahl für neue Aufträge und
Dialoge ausblenden und später wiederherstellen. Die Seite ist aus Auftrag, Dialog
und Provider-Einstellungen erreichbar.

Archivieren ordnet die Auswahl. Es beendet keine laufenden Aufträge und sperrt keine
Berechtigungen. Bestehende Dialoge, Downloads, Freigaben und Wiederaufnahmen bleiben
nutzbar. Auch die CLI und ein ausdrücklich angegebener Agentenpfad können weiter
arbeiten. Zum Stoppen eines laufenden Vorgangs ist Archivieren daher ungeeignet.

Die Anwendung verschiebt oder löscht weder Agentenpakete noch Workspaces. Der
Archivstatus liegt separat unter `cockpit/.runs/assistant-settings/` und gehört in
die normale Zustandssicherung. Wiederholtes Setzen desselben Status ist idempotent.
Ungültige Metadaten führen zu einem sichtbaren Fehler statt stiller Wiederherstellung.

Die Archivverwaltung ändert keine Identität, Company, Rollen oder Skills bestehender
Agenten. Diese strukturellen Eigenschaften sind im Vorgabeneditor nicht bearbeitbar.

Geprüft: HTTP-Origin-Schutz, wiederholtes Setzen, Neustart, ungültige Metadaten und
Packs, unveränderte Agentenkonfiguration, Originalanhang-Download und vollständiger
Demo-Freigabeablauf während der Archivierung. Browser-Abnahme in separatem Testzustand:
Archivieren, Reload, ausgeblendete Neuauswahl, Wiederherstellen und fehlgeschlagener
POST bei gestopptem Server mit anschließendem bewusstem Neuladen. Kein Live-Modelltest.
