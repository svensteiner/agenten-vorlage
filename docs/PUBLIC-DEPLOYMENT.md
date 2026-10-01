# Öffentlicher Single-Tenant-Mehrbenutzerbetrieb

Der öffentliche Einstiegspunkt `cockpit.public_server` ist eine eigene sichere
Control Plane. Er verwendet für jeden authentifizierten Nutzer getrennte Agenten-,
Workspace- und Zustandsverzeichnisse. Der lokale Server `cockpit.server` bleibt ein
Loopback-Werkzeug und darf nicht als Internetdienst veröffentlicht werden.

## Unterstützter Scope

Der Public-Modus unterstützt:

- OIDC-Anmeldung hinter TLS;
- einen serverseitig festgelegten Tenant mit mehreren getrennten Nutzern;
- die Rollen `viewer`, `member`, `reviewer` und `tenant_admin` aus dem OIDC-`groups`-Claim;
- Demo sowie optional DeepSeek mit `list_files`, `read_file`, `write_file` und `edit_file`;
- begrenzte UTF-8-Textanhänge, Dialoge, Freigaben und Artefakte;
- sitzungsgebundenes CSRF, Origin-Prüfung, Rate-/Job-/Speichergrenzen und HMAC-Audit.

Die Speichergrenze zählt den vollständigen Nutzerbaum aus Agenten, Workspaces,
Dialogen, Anhängen und Jobzuständen. Alle dauerhaften Nutzer- und Modellmutationen
prüfen Bytes, Dateien und Verzeichnisse atomar direkt vor dem Dateiersatz; abgewiesene
Schreibvorgänge hinterlassen keine neuen Verzeichnisbäume.

Der öffentliche Scope **excludes Codex execution**, `run_pytest`, Test- und
Fremdcodeausführung, Hostpfade, Binärdateien sowie PDF-/Office-/Bildparser.
**Text attachments** sind die einzige öffentliche Anhangsart. Diese Begrenzung ist Teil der
Sicherheitsarchitektur. Fremdcode benötigt später einen separaten isolierten Worker.

Die aktuelle Vorlage betreibt genau eine App-Instanz. Prozesslokale Limits und der
dateibasierte Zustand sind nicht horizontal skalierbar. Mehrere Firmen/Tenants oder
mehrere App-Replikate benötigen gemeinsame Datenbank, Objektablage, Queue und
verteilte Limits.

## Voraussetzungen

- Linux-Host mit aktueller Docker Engine und Compose v2;
- `linux/amd64` und ein gepinntes CPython-3.12-Basisimage; die öffentlichen
  Build-/Runtime-Lockdateien sind absichtlich auf diese Plattform geschlossen;
- öffentlicher DNS-Name und gültiges Zertifikat;
- OIDC-Client mit Callback `https://HOST/oauth2/callback`;
- OIDC-Claims `email` und `groups`;
- mindestens eine erlaubte Gruppe und interne Rollen als Gruppenwerte;
- unveränderliche `image@sha256:...`-Referenzen für die gebaute App, ein aktuell
  gepatchtes Debian-basiertes Python-Image, OAuth2 Proxy mindestens 7.15.4 und Caddy
  mindestens 2.11.4;
- externes Backupziel, Monitoring und ein Secret-Store.

Ein Nutzer muss Mitglied der konfigurierten `AGENTKIT_AUTH_ALLOWED_GROUP` sein und
zusätzlich mindestens eine Gruppe mit exakt einem der Namen `viewer`, `member`,
`reviewer` oder `tenant_admin` erhalten. Üblich ist, alle Nutzer in `member` und
Freigabeverantwortliche zusätzlich in `reviewer` zu führen.

## 1. Nicht geheime Einstellungen

Im Repository:

```bash
cp deploy/public/public.env.example deploy/public/public.env
```

In `deploy/public/public.env` Host, Origin, Tenant, OIDC-Issuer, Client-ID, Domain und
Gruppen anpassen. Für App-, Basis- und Proxy-Images zuerst die freigegebenen Images
ziehen beziehungsweise mit `docker buildx imagetools inspect` prüfen und anschließend
die vollständige RepoDigest-Referenz eintragen. Tags allein sind nicht zulässig.

Vor jeder Compose-Änderung prüft der versionierte Digest-Gate alle drei öffentlichen
Images deterministisch. Auf einem Host mit Registry-Zugriff prüft `--verify` zusätzlich,
dass Docker Buildx die Referenzen auflösen kann:

```bash
python scripts/check_public_image_digests.py --env-file deploy/public/public.env
python scripts/check_public_image_digests.py --env-file deploy/public/public.env --verify
```

Die Datei `public.env.example` enthält außerdem sämtliche einstellbaren Runtime-Limits:
Anfragen, Nutzer und Runtime-Cache, Speicher und Dateien, Jobs, parallele Worker und
Auditgröße. Der Public-Prozess validiert diese Werte beim Start und beendet sich bei
fehlenden oder außerhalb der Grenzen liegenden Einstellungen.

`AGENTKIT_PUBLIC_BACKENDS=demo` ist der sichere Standard. DeepSeek bleibt opt-in und
benötigt neben dem Provider-Key eine separat freigegebene Egress-Netzwerkregel für den
App-Container. Das Compose-Stack hängt ausschließlich die App an das eigene, nicht
interne `egress`-Bridge-Netz (`172.32.0.0/24`); Caddy und OAuth2 Proxy erhalten dort
keinen Netzwerkzugang. Vor Aktivierung muss der Docker-Host beziehungsweise die
Cloud-Firewall ausgehende Verbindungen dieses Netzes auf `api.deepseek.com:443`
begrenzen. Ohne diese Allowlist und einen erfolgreichen Egress-Smoke darf DeepSeek
nicht aktiviert werden.

## 2. Secrets und Zertifikat

Die Verzeichnisse sind von Git ausgeschlossen:

```bash
mkdir -p deploy/public/secrets deploy/public/certs
python - <<'PY'
from pathlib import Path
import secrets

root = Path("deploy/public/secrets")
(root / "csrf_secret").write_bytes(secrets.token_bytes(32))
(root / "identity_secret").write_bytes(secrets.token_bytes(32))
PY

# OAuth2 Proxy requires raw binary, exactly 16, 24 or 32 bytes.
openssl rand -out deploy/public/secrets/session_cookie_secret 32
```

Danach manuell aus dem Secret-Store anlegen:

- `deploy/public/secrets/oidc_client_secret`
- `deploy/public/secrets/provider_credentials.json` mit
  `{"deepseek_api_key":"..."}`
- `deploy/public/certs/tls.crt`
- `deploy/public/certs/tls.key`

Secrets niemals in Shell-History, Tickets, Aufgaben, Logs oder Git schreiben. CSRF-
und Identity-Secret müssen mindestens 32 Bytes lang sein; das Session-Cookie-Secret
muss genau 32 rohe Bytes enthalten und darf nicht als Base64-Text gespeichert werden.
Eine Rotation des
Identity-Secrets ändert die opaken Nutzerpfade und benötigt deshalb eine geplante
Datenmigration.

## 3. Konfiguration prüfen und Image bauen

```bash
set -a
. ./deploy/public/public.env
set +a

docker compose \
  --env-file deploy/public/public.env \
  -f deploy/public/docker-compose.production.yml config --quiet

docker buildx build \
  --platform linux/amd64 \
  --build-arg PYTHON_BASE_IMAGE="$AGENTKIT_PYTHON_BASE_IMAGE" \
  --tag registry.example.com/company/agentkit-public:2026.10.01-1 \
  --push \
  -f Dockerfile.public .

docker buildx imagetools inspect registry.example.com/company/agentkit-public:2026.10.01-1
# Set AGENTKIT_APP_IMAGE in public.env to the resulting
# registry.example.com/company/agentkit-public@sha256:... RepoDigest.
```

Der CI-Gate baut und startet dasselbe Image bereits mit `linux/amd64`, dem im Image
festgelegten Benutzer `10001:10001` und einem temporären Secret-Satz. Er wartet auf
`/api/readiness`; ein grüner Build belegt damit den Containerstart und die Readiness-
Initialisierung, ersetzt aber nicht die Staging-Abnahme mit realem OIDC und TLS.

Der TLS-Proxy entfernt eingehende `X-Forwarded-*`-Identitätsheader sowie alle
`X-Agent-*`-Header vor dem Auth-Proxy; OAuth2 Proxy
setzt danach ausschließlich die verifizierten `X-Forwarded-Email`, `X-Forwarded-Groups`
und `X-Forwarded-User`-Werte. Der Auth-Proxy läuft mit
`--skip-auth-strip-headers=false`. Der Edge begrenzt Request-Bodies auf 3 MiB. Das
deckt den öffentlichen Upload-Vertrag ab; Rate-Limits bleiben zusätzlich in der App,
weil Caddy ohne Zusatzmodul keinen verteilten Rate-Limiter bereitstellt.

Das Python-Basisimage wird vom Dockerfile nur als vollständig gepinnte Digest-
Referenz akzeptiert. Compose verwendet ausschließlich `AGENTKIT_APP_IMAGE` mit
`@sha256`; ein Build-Tag ist nur ein Zwischenartefakt und wird nicht deployt. Der Build
lädt ausschließlich die exakten Wheels aus `requirements-build.lock` und
`requirements-runtime.lock` mit verifizierten SHA-256-Hashes; `pytest` ist kein Teil
des öffentlichen Runtime-Images. Eine Plattform- oder Dependency-Aktualisierung
erfordert eine bewusste Neuberechnung und Prüfung dieser Hashes. Der Build
kopiert keine lokalen Runs, Tests, Secrets oder generierten privaten Agenten. Vor dem
Start Image scannen, SBOM ablegen, die RepoDigest protokollieren und den Release-Tag
gegen Überschreiben schützen.

Das `egress`-Bridge-Netz ist eine kontrollierte Anschlussstelle, keine Provider-
Allowlist. Die Allowlist muss auf dem Zielhost oder in der Cloud-Netzwerkebene
durchgesetzt werden; Compose und Caddy stellen keinen verteilten Egress- oder
Rate-Limiter bereit.

## 4. Staging starten

```bash
docker compose \
  --env-file deploy/public/public.env \
  -f deploy/public/docker-compose.production.yml up -d

docker compose \
  --env-file deploy/public/public.env \
  -f deploy/public/docker-compose.production.yml ps
```

Nur Caddy veröffentlicht Port 80/443. OAuth2 Proxy und App liegen in privaten
Netzen. Die App besitzt kein Docker-Socket, keine Host-Workspaces, keine Linux-
Capabilities und ein read-only Root-Dateisystem. Das persistente `app_data`-Volume
ist die einzige schreibbare dauerhafte Datenfläche.

`/api/health` belegt nur Prozess-Liveness. `/api/readiness` ist das Traffic-Gate und
wird fail-closed, wenn ein unsicheres Backend aktiviert oder für DeepSeek kein
Provider-Key vorhanden ist. Das Endpoint prüft keine externe DeepSeek-Erreichbarkeit;
deren Egress-Smoke gehört zur Staging-Abnahme.

## 5. Verbindliche Staging-Abnahme

Vor Internetfreigabe alle Punkte mit einem realen Browser und mindestens zwei
Identitäten belegen:

1. OIDC Login, Logout, abgelaufene/rotierte Sitzung und Gruppenentzug;
2. falscher Host, HTTP, direkte App-Verbindung und eingespeiste Identity-Header scheitern;
3. Mutation ohne beziehungsweise mit falschem CSRF/Origin scheitert;
4. Alice sieht Bobs Job, Dialog, Anhang und Artefakt nicht;
5. `viewer` darf lesen, `member` starten, `reviewer` freigeben;
6. Edge-Body-, Rate-, Job-, Upload-, Datei- und Volumengrenzen liefern kontrollierte Fehler;
7. Demo endet nach Freigabe und Review; DeepSeek-Smoke nur bei aktiviertem Backend;
8. Antworten, Browser, Logs und Audit enthalten keine Hostpfade, Tokens oder Secrets;
9. Last-/Soak-Test hält CPU, RAM, Threads und Volume innerhalb der Zielwerte;
10. unabhängiger Security- und Penetrationstest bleibt ohne offenen hohen Befund.

The repository tests are **not evidence** that an unknown public deployment is safe.
Production acceptance still requires a **real
OIDC provider**, real TLS, target-host backup/restore, representative load and
**independent security and** penetration testing.

## Backup, Restore und Rollback

Für ein konsistentes Backup Zugriffe stoppen oder einen atomaren Volume-Snapshot von
`app_data` erstellen. Auditdateien und alle Secrets getrennt, verschlüsselt und mit
Zugriffsprotokoll sichern. Restore zuerst in Staging durchführen und Identitätsmapping,
Dialoge, Anhänge, wartende Freigaben, Artefakte, Auditkette und Readiness prüfen.

Rollback verwendet das vorherige gebaute App-Image sowie dieselben gepinnten Proxy-
Images. Vor Schemaänderungen muss der Dateizustand rückwärtskompatibel oder migrierbar
bleiben. Ein Daten-Rollback kann bereits ausgeführte externe Aktionen nicht rückgängig
machen.

## Betrieb und Alarmierung

Keine Prompts, Anhänge, E-Mail-Adressen, Cookies, Tokens oder Provider-Keys in Logs und
Metriklabels aufnehmen. Mindestens auf Readiness, 401/403/429-Raten, 5xx-Rate, aktive
Jobs, CPU/RAM, Volume-Füllstand, Audit-Integritätsfehler und Backupfehler alarmieren.
Der lokale Auditpuffer rotiert begrenzt, prüft seine HMAC-Kette und verweigert nach
Initialisierung einen Neustart, wenn Log, lokaler Marker oder separater Volume-
Bootstrap-Marker fehlen. Er ersetzt kein externes append-only Logarchiv; Löschung des
gesamten lokalen Volumes muss extern erkannt werden.
