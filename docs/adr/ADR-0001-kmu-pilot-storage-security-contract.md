# ADR-0001 - Storage-Sicherheitsvertrag für den KMU-Piloten

- **Status:** Proposed; required for production
- **Datum:** 2026-07-22
- **Entscheider:** Pilotbetrieb, Plattformbetrieb und Security
- **Geltungsbereich:** Jede produktive KMU-Controlling-Instanz und ihre Storage-Bereitstellung

## Kontext

Der Pilot speichert Konfiguration und Regeln unter `project/`, Lauf- und
Abnahmenachweise unter `state/`, Laufzeitdaten unter `state/runtime/` sowie
Berichte unter `artifacts/`. Mandanten dürfen Quelldateien ausschließlich
unter `inbox/`, `data/` oder `imports/` bereitstellen.

Die Anwendung prüft Pfade und lehnt bekannte symbolische Links an mehreren
Schreibstellen ab. Solche Preflights sind sinnvoll, schließen aber einen
Austausch eines Verzeichnisses oder Links zwischen Prüfung und Zugriff nicht
aus. Besonders bei mehreren Mandanten unter demselben Betriebssystemkonto kann
portable Python-Logik keine belastbare Mandantengrenze herstellen.

## Threat Model und Sicherheitsziel

Der **Servicebetreiber und die von ihm kontrollierte Service-Identität sind
vertrauenswürdig**. Der **Mandant und alle von ihm angelieferten Dateien,
Verzeichnisobjekte und Metadaten sind nicht vertrauenswürdig**. Geschützt
werden müssen Konfiguration, Kontrollzustand, Laufbuch, Signaturschlüssel,
Berichte, die Eingaben aller anderen Mandanten und die Storage-Grenze selbst.
Kein Mandant und kein mandantenspezifischer Dienst darf Eingaben eines anderen
Mandanten lesen, auflisten, schreiben, löschen oder umbenennen. Der jeweils
eigene Mandant darf ausschließlich seine eigenen freigegebenen Eingabebäume
beschreiben.

Mehrere nicht gegenseitig vertrauenswürdige Mandanten unter demselben
OS-Principal zu betreiben ist **nicht unterstützt**. Ein logischer
`tenant_id`, ein HMAC-verkettetes Laufbuch und Anwendungs-Preflights ersetzen
keine Betriebssystem- oder Deployment-Isolation.

## Entscheidung

Eine produktive Instanz darf erst freigegeben werden, wenn die folgenden
Eigenschaften für die konkrete Bereitstellung nachgewiesen sind:

1. **Eigene eingeschränkte Service-Identität je Tenant.** Jeder Tenant läuft
   unter einer eigenen, nicht interaktiv genutzten OS-Service-Identität. Eine
   gemeinsam privilegierte Service-Identität für mehrere Tenants ist nicht
   zulässig.
2. **Eigener Ausführungsscope je Tenant.** Jeder Tenant erhält einen eigenen
   Prozess und einen eigenen Container-, VM- oder Namespace-Scope mit eigenem
   Volume-Scope. Volumes und Pfade anderer Tenants sind dort weder gemountet
   noch anderweitig erreichbar. ACLs härten diese Grenze zusätzlich, sind aber
   allein keine ausreichende Produktionsisolation.
3. **Servicekontrollierte Parentkette.** Ein vertrauenswürdiger
   Provisionierungsdienst kontrolliert den attestierten Storage-Root und die
   Parentkette. Die eingeschränkte Tenant-Service-Identität kann nur ihren
   eigenen Instanzscope erreichen. Mandanten können Parentkomponenten weder
   anlegen, ersetzen, umbenennen noch löschen und dort keine Links oder
   Reparse-Points erzeugen.
4. **Servicekontrollierte Steuerbereiche.** `project/`, `state/`,
   `state/runtime/` (und jeder anders konfigurierte Runtime-Pfad) sowie
   `artifacts/` sind für den Mandanten nicht schreibbar. Das gilt auch für
   deren Parentverzeichnisse, Lock- und Temp-Dateien. Nur die eingeschränkte
   Service-Identität dieses Tenants führt dort Anwendungs-Schreibzugriffe aus.
5. **Begrenzte eigene Mandanten-Schreibfläche.** Der Mandant erhält
   Schreibrechte ausschließlich in seinen eigenen Verzeichnissen `inbox/`,
   `data/` und `imports/`. Eingabebäume anderer Tenants darf er weder lesen
   noch auflisten, schreiben, löschen oder umbenennen. Ein Eintrag im eigenen
   Eingabebaum darf keinen Zugriff außerhalb des eigenen Volume-Scopes
   bewirken. Leserechte auf freigegebene eigene Berichte werden separat nach
   dem Least-Privilege-Prinzip vergeben; sie begründen kein Schreibrecht auf
   `artifacts/`.
6. **Defense-in-depth.** OS-ACLs und Anwendungs-Preflights ergänzen die
   Prozess-/Namespace-/Volume-Isolation. Die bestehenden Pfad- und
   Symlink-Preflights bleiben aktiv, sind aber weder Sicherheitsgrenze noch
   Produktionsnachweis.

### Anforderungen an Windows-Bereitstellungen

- Für jeden Tenant existiert eine eigene eingeschränkte Service-Identität. Der
  Provisionierungsdienst besitzt die übergeordnete Parentkette; die
  Tenant-Service-Identität erhält ausschließlich die für ihren eigenen Scope
  erforderlichen Rechte.
- Mandantenidentitäten und fremde Tenant-Service-Identitäten erhalten auf
  Parentkette, Steuerbereiche und fremde Eingabebäume insbesondere weder
  `DELETE` noch `FILE_DELETE_CHILD`, `WRITE_DAC`, `WRITE_OWNER`/Take Ownership
  oder andere Rechte zum Schreiben, Ändern, Ersetzen, Löschen und Erzeugen von
  Unterobjekten.
- DACL-Vererbung und effektive Rechte werden für jede Komponente der
  Parentkette sowie für alle genannten Instanzbereiche explizit geprüft. Eine
  unerwartete geerbte Schreibberechtigung ist ein Abnahmefehler.
- Reparse-Points und andere Umleitungen dürfen die kontrollierte Grenze nicht
  durchbrechen. Entscheidend ist der separate Prozess-/Container-/VM- und
  Volume-Scope; DACLs sind eine zusätzliche Barriere.

### Anforderungen an Linux-Bereitstellungen

- Jeder Tenant-Dienst läuft unter einer eigenen eingeschränkten Service-UID in
  einem eigenen Prozess-/Container-/VM- und Namespace-/Volume-Scope. Kein
  fremdes Tenant-Volume wird eingebunden.
- Die Parentkette und Steuerbereiche sind für Mandanten-UIDs, fremde
  Service-UIDs, gemeinsam genutzte Gruppen und `other` nicht schreibbar. Auf
  Parentverzeichnissen werden `write` und das für Änderung notwendige
  Zusammenspiel aus `write` + `execute` ausdrücklich geprüft; `execute` wird
  nur für erforderliche Traversierung im eigenen Scope vergeben.
- POSIX-ACLs, Mode-Bits, Mounts, effektive Gruppen, ACL-Masken und Default-ACLs
  werden gemeinsam geprüft. ACL-Masken und Default-ACLs dürfen effektive oder
  neu vererbte Rechte nicht aufweiten.

Diese ADR enthält bewusst keine Copy/Paste-Befehle für ACL-Änderungen. Die
korrekte Umsetzung hängt von Host, Identitätsmodell, Vererbung und
Deploymentform ab; ungetestete Befehle können Daten sperren oder Rechte
unbeabsichtigt erweitern.

## Migration bestehender Instanzen

Ein Baum, der jemals für einen Mandanten außerhalb der drei Eingabebereiche
schreibbar war, wird **offline neu provisioniert** und nicht im laufenden
Betrieb lediglich umberechtigt:

1. Dienst und Mandantenzugriff stoppen und den Altbaum unverändert sichern.
2. Unter einer frisch attestierten, servicekontrollierten Parentkette eine neue
   Instanz mit eigener eingeschränkter Service-Identität und eigenem
   Prozess-/Container-/VM-/Namespace-/Volume-Scope anlegen; fremde
   Tenant-Volumes nicht einbinden. Danach die zusätzlichen ACLs anwenden.
3. Nur erwartete reguläre Dateien als Servicebetreiber übernehmen. Keine
   Ownership-, ACL-, Link-, Reparse-Point- oder Spezialdatei-Metadaten aus dem
   tenant-writablen Baum fortschreiben; unerwartete Objekte stoppen die
   Migration.
4. Inhalt und erwarteten Dateibaum gegen eine freigegebene Inventarliste bzw.
   kryptografische Digests prüfen. Danach negative Zugriffs- und
   Wiederanlauftests unter Service- und Mandantenidentität ausführen.
5. Erst nach dokumentierter Abnahme den neuen Baum aktivieren und
   Mandantenschreibrechte ausschließlich für `inbox/`, `data/` und
   `imports/` öffnen. Der Altbaum bleibt außerhalb des aktiven Mounts
   quarantiniert und folgt dem genehmigten Aufbewahrungsprozess.

## Produktionsnachweis und offener P1

Der P1 **Mandantentrennung/Storage** bleibt offen, bis ein aktueller,
reproduzierbarer manueller Nachweis für das reale, produktionsgleiche Zielsystem
vorliegt. Der Nachweis wird an einem servicekontrollierten Ablageort außerhalb
aller Tenant-Volumes unveränderbar bzw. zugriffsgeschützt abgelegt und enthält:

- absoluten Storage-Root, Tenant-ID, eingeschränkte Service- und
  Mandantenidentität sowie Zeitstempel, Zielumgebung und definierte
  Gültigkeitsdauer;
- Fingerprints der Deploymentdefinition, des tatsächlich gestarteten Images,
  der Prozess-/Container-/VM-/Namespace- und Volume-Zuordnungen sowie der
  effektiven ACLs einschließlich Parentkette;
- eine ausführbare Testmatrix mit Testidentität, Ausgangszustand, Aktion,
  Zielpfad, erwartetem Ergebnis und beobachtetem Ergebnis;
- Sign-off von Plattformbetrieb und Security mit Verweis auf die geprüften
  Fingerprints und Testergebnisse.

Die Testmatrix muss mindestens folgende Soll-Ergebnisse reproduzieren:

| Test | Identität und Aktion | Soll-Ergebnis |
| --- | --- | --- |
| Eigener Input | Mandant schreibt, liest, listet, benennt um und löscht eine synthetische Datei in den eigenen `inbox/`, `data/` und `imports/` | Nur im jeweils eigenen Eingabebaum erfolgreich |
| Eigene Steuerbereiche | Mandant versucht Lesen/Listen sowie Schreiben, Löschen und Umbenennen in `project/`, `state/`, Runtime und `artifacts/` | Verweigert, soweit keine separat freigegebene Lesesicht besteht; jede Mutation verweigert |
| Fremder Scope | Mandant und eigener Tenant-Dienst versuchen Lesen, Listen, Schreiben, Löschen und Umbenennen in Eingabe- und Steuerbereichen eines zweiten synthetischen Tenants | Fremdes Volume nicht gemountet/erreichbar; keine Cross-Scope-I/O |
| Link-/Junction-E2E | Mandant erzeugt im eigenen Eingabebaum einen Symlink, unter Windows zusätzlich eine Junction/Reparse-Point-Variante, auf einen synthetischen fremden Scope; anschließend verarbeitet der eigene Dienst den Input | Dienst lehnt den Input fail-closed ab; im fremden Scope erfolgen weder Lesen/Listen noch Schreiben, Löschen oder Umbenennen |
| Eigener Dienst | Eigene Tenant-Service-Identität schreibt erforderliche State-, Runtime- und Artefaktdateien | Nur im eigenen Scope erfolgreich |
| Neustart | Deployment wird mit denselben Fingerprints neu gestartet und die Negativtests werden wiederholt | Isolation und Soll-Ergebnisse unverändert |

Der E2E-Linktest wird innerhalb der tatsächlich ausgelieferten
Prozess-/Container-/VM-/Namespace-/Volume-Konfiguration ausgeführt, nicht nur
gegen eine Pfadprüffunktion. Cross-Scope-I/O wird durch Betriebssystem-/Storage-
Audit oder eine gleichwertige, überprüfbare Beobachtung ausgeschlossen.

Jede Änderung an Image, Deploymentdefinition, Identitäten, ACLs,
Parentkette, Mounts/Volumes oder Gültigkeitsdauer macht die betroffene Evidenz
ungültig und öffnet den P1 erneut. Die CLI-Ampel `GRÜN – pilotbereit` ist
notwendig, aber für die Produktionsfreigabe nicht hinreichend. Ein lokaler
Testlauf unter nur einem OS-Principal, ein sauberer Anwendungstest oder ein
erfolgreicher Preflight schließt diesen P1 nicht.

`python agent_cli.py status --instance <pfad> --production` prüft zusätzlich
eine Referenz, die nur eine opaque Attestation-ID enthält. Der
servicekontrollierte Trust Root wird ausschließlich über
`AGENT_PRODUCTION_TRUST_ROOT` konfiguriert; UNC-, Link-/Reparse- und
Tenant-Volume-Pfade werden abgelehnt. Darunter liegen feste Pfade für die
Attestation, zwei unabhängig per Ed25519 geprüfte Platform-/Security-Signaturen
und separat unter `runtime/<tenant>/<agent>/` signierte, höchstens 15 Minuten alte Runtime-Fakten. Diese müssen
Tenant, Agent, Generation, Service-Identität und alle vier Fingerprints exakt
an die höchstens 30 Tage gültige Attestation binden. Ohne diese aktuelle,
signierte Evidenz bleibt die Produktionsfreigabe rot; die lokale Pilot-Ampel
wird dadurch niemals als Produktionsfreigabe interpretiert.

Der ausgelieferte, geschützte Paket-Build enthält den Ed25519-Control-Plane-
Root-Key als Trust Anchor. Der Trust Root muss eine von diesem Key signierte,
kurzlebige `trust-config.json` mit drei SHA-256-Key-Pins enthalten; fehlende,
falsche oder doppelte Schlüssel/Pins sperren die Freigabe. Der Provisioner
liefert den autorisierten Root-Key im Build und die Signatur aus. Ein
Platzhalter-Build ohne autorisierte Signatur bleibt fail-closed. Trust Root,
Trust-Konfiguration und Root-Key sind Teil des Deployment-Fingerprints und
dürfen weder aus der Tenant-Referenz noch aus dem Tenant-Dateibaum stammen.

## Verworfene Alternativen

- **Gemeinsame privilegierte Service-Identität mit ACL-Trennung:** verworfen;
  eine Fehlkonfiguration oder Kompromittierung erreicht mehrere Tenants.
- **Nur ACLs auf einer gemeinsamen Host-Struktur:** verworfen; ACLs sind
  zusätzliche Härtung, nicht die alleinige Produktionsgrenze.
- **Nur Anwendungs-Preflight:** verworfen; Prüf- und Zugriffszeitpunkt können
  auseinanderfallen.

## Konsequenzen

- Produktive Pilotabnahme ist ohne Deploymentnachweis blockiert, auch wenn die
  fachlichen Kennzahlen und Wiederholungslauf-Kriterien bestanden sind.
- Entwicklung und synthetische Demo unter einem lokalen Principal bleiben
  möglich, dürfen aber nicht als Nachweis produktiver Mandantentrennung
  bezeichnet werden.
- Anwendungs-Preflights bleiben erhalten und können erweitert werden; ihre
  Rolle ist Fehlererkennung und Defense-in-depth, nicht Isolation.
- Der manuelle Produktionsnachweis muss nach jeder sicherheitsrelevanten
  Deploymentänderung erneuert und erneut freigezeichnet werden.
