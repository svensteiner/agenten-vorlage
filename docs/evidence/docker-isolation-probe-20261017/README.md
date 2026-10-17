# Vorpruefung fuer isolierte Agententests

Der echte synthetische Docker-Test am 17.10.2026 besteht mit Exit 0.
Zehn Containerpruefungen und zwoelf Hostpruefungen bestehen; die geschuetzte
Hostdatei bleibt bytegleich, der eindeutig benannte Container wird entfernt.
Das offizielle Python-Image ist auf den im Resultat erfassten Digest gebunden.
Die Docker-Einstellungen folgen der [offiziellen Laufzeitdokumentation](https://docs.docker.com/engine/containers/run/).

Geprueft: Netzwerkzugriff verweigert, Workspace/Root schreibgeschuetzt,
UID 65534, keine effektiven Capabilities, no-new-privileges, kein Docker-Socket,
keine Host-Mountwurzel oder API-Key-Umgebungsvariablen. Docker-inspect bestaetigt
einen einzigen schreibgeschuetzten synthetischen Bind-Mount, begrenztes Tmpfs,
128 MiB RAM ohne zusaetzlichen Swap, eine CPU, 32 PIDs und 64 Dateideskriptoren.
Fehlende Pruefung, falsche Einstellung oder geaenderte Hostdatei erzwingt Fehler.
Die separate Code-/Sicherheitspruefung fand nach Ergaenzung dieser Hostabnahme
keinen konkreten Blocker. Rohresultat und ausgefuehrter Helper sind beigefuegt.

**Grenzen:** Kein Projektcode und kein Modellauftrag liefen darin. Kein Beweis
gegen Kernel-/Docker-Schwachstellen. Noch kein AgentKit-Testwerkzeug und keine
Freigabe beliebigen Codes. Die strikte WritePolicy sperrt run_pytest weiterhin.
Das offizielle Image allein enthaelt noch keine vorbereiteten Projektabhaengigkeiten.

## Erforderliche Integration

Der Host muss das Image samt vertrauenswuerdigen, gebundenen Abhaengigkeiten
vorgeben; der Agent darf weder Image, Dockerfile, Mounts noch Startargumente
veraendern. Nur ein kuratierter Quellsnapshot ohne Zugangsdaten, Git-Verweise,
Links oder Hostkonfiguration darf hinein. Der aktuelle Workspace bleibt
schreibgeschuetzt. Testcache und temporaere Dateien bleiben im begrenzten Tmpfs.
Ein eigener Toolvertrag muss Zeit- und Ausgabelimits, Prozessabbruch samt
Containerbereinigung, Hashbindung des Testergebnisses und Review-Invalidierung
bei jeder weiteren Aenderung durchsetzen. Erfolgreiche Tests sind keine
inhaltliche Abnahme. Ausfall der Isolation muss Tests sperren, niemals auf
unbegrenztes Host-pytest zurueckfallen. Resume darf einen unbekannten Lauf
nicht automatisch nochmals starten.

Erst nach Integration und Gegenproben kann ein echter Coding-Auftrag zeigen,
dass der Agent seine eigenen Fehler damit autonom findet und behebt.
