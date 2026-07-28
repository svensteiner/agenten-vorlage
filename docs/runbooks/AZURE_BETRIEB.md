# Azure-Betrieb und kundeneigenes LLM

Stand: 28. Juli 2026

## Produktmodell

AIStudioXYZ betreibt die Plattform. Ein vermieteter Agent ist keine eigene
virtuelle Maschine, sondern eine logisch getrennte Instanz aus:

- Kunde (`tenant_id`)
- Agentenrolle und Fachkonfiguration
- erlaubten Werkzeugen und Datenquellen
- eigenem Daten-, Rechte- und Kostenbereich

Mehrere Agenten eines Kunden dürfen sich eine technische Laufzeit teilen. Die
Sicherheits- und Abrechnungsgrenze ist grundsätzlich der Kunde, nicht der Agent.

## Drei Betriebsprofile

| Profil | Betrieb | Geeignet für | Kostenwirkung |
|---|---|---|---|
| **Standard** | Gemeinsame AIStudioXYZ-Plattform auf Azure; Daten und Rechte strikt je Kunde getrennt | die meisten KMU | niedrigste Kosten pro Agent |
| **Isoliert** | Eigene Azure-Ressourcen je Kunde, weiterhin von AIStudioXYZ betrieben | regulierte oder besonders vorsichtige Kunden | eigener fixer Infrastruktur-Sockel |
| **Kunden-LLM** | Der Modellaufruf geht ausschließlich an einen privaten, OpenAI-kompatiblen Endpunkt des Kunden | maximale Modell- und Promptkontrolle | eigene GPU-/Betriebskosten beim Kunden |

Solange der produktive Nachweis der gemeinsamen Mandantentrennung noch offen
ist, wird der erste Echtdaten-Pilot isoliert je Kunde betrieben. Das ist eine
vorübergehende Sicherheitsentscheidung und bedeutet **nicht** eine Azure-Box je
Agent. Nach bestandenem Isolationstest können Standardkunden ohne Änderung der
Agentenlogik in den gemeinsamen Betrieb wechseln.

## Azure als Standard

Für den produktiven Azure-Pfad gelten:

1. Azure Container Apps beziehungsweise ein geplanter Container-Apps-Job führt
   den Agenten aus.
2. Jede Kundeninstanz erhält eine eigene Managed Identity und einen eigenen
   Datenbereich.
3. Secrets liegen in Azure Key Vault, nicht in Dateien oder Agenten-Prompts.
4. Modellaufrufe laufen über Azure OpenAI beziehungsweise Microsoft Foundry.
5. Der Modellname ist eine Deployment-Konfiguration. Die Fachlogik kennt keinen
   konkreten Modellanbieter.
6. Günstige Modelle erledigen Routineaufgaben; ein stärkeres Modell wird nur
   für begründete komplexe Aufgaben verwendet.

Minimale Konfiguration:

```dotenv
LLM_PROVIDER=azure
APP_ENV=production
AZURE_OPENAI_ENDPOINT=https://NAME.openai.azure.com
AZURE_OPENAI_USE_MANAGED_IDENTITY=true
AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4.1-nano
AZURE_OPENAI_DEPLOYMENT_SMART=gpt-4.1-mini
AZURE_OPENAI_MODEL_FAMILY=gpt-4.1
```

Für lokale Entwicklung kann statt Managed Identity vorübergehend
`AZURE_OPENAI_API_KEY` gesetzt werden. Produktiv bleibt der Key leer.
Der Modellfamilienwert beschreibt die Fähigkeiten des Modells unabhängig vom
frei wählbaren Azure-Deploymentnamen. Bei Reasoning-Modellen wird
`AZURE_OPENAI_REASONING_EFFORT` ausdrücklich passend zum bereitgestellten
Modell gesetzt; die Anwendung rät diesen Wert nicht aus dem Namen.

## Kundeneigenes LLM

Der optionale Kundenpfad erwartet einen OpenAI-kompatiblen HTTPS-Endpunkt, zum
Beispiel vor einem vLLM-Modellserver. Er ist absichtlich eng:

- Remote-Endpunkte müssen HTTPS verwenden; unverschlüsseltes HTTP ist nur auf
  der lokalen Maschine zulässig.
- Ein kundeneigenes LLM fällt bei einer Störung **nicht** still auf Azure
  zurück. Der Lauf stoppt oder wartet.
- Modell-ID und freigegebene Modellversion sind feste Konfiguration.
- Logs enthalten Laufzeit, Tokenzahlen und Status, aber keine Prompts,
  Rohbuchungen oder Zugangsdaten.
- Der Endpunkt erhält nur die Daten, die für den jeweiligen Lauf erlaubt sind.

Minimale Konfiguration:

```dotenv
LLM_PROVIDER=onprem
APP_ENV=production
DEPLOYMENT_TENANCY=isolated
ONPREM_LLM_BASE_URL=https://llm.kunde.example/v1
ONPREM_LLM_ALLOWED_HOSTS=llm.kunde.example
ONPREM_LLM_API_KEY=
ONPREM_LLM_MODEL=freigegebene-modell-id
```

Für eine kundeneigene Zertifizierungsstelle oder mTLS stehen zusätzlich
`ONPREM_LLM_CA_BUNDLE`, `ONPREM_LLM_CLIENT_CERT` und
`ONPREM_LLM_CLIENT_KEY` zur Verfügung.

Wichtig: Ein LLM beim Kunden bedeutet nicht automatisch, dass auch alle
Anwendungsdaten beim Kunden liegen. Verlangt der Kunde vollständige
Datenhoheit, müssen zusätzlich Anwendung, Speicher und Datenbank in dessen
Azure-Umgebung oder Rechenzentrum betrieben werden.

## Plug-and-Play-Abnahme

Ein Profil gilt erst dann als einsatzbereit, wenn diese vier Prüfungen bestehen:

1. Konfiguration und Modell sind erreichbar.
2. Ein synthetischer Testlauf erzeugt dasselbe Ergebnis dreimal.
3. Ein negativer Test beweist, dass kein nicht erlaubter Modellendpunkt genutzt
   wird.
4. Bei fehlendem Modell, Secret oder Kundenkontext stoppt der Lauf sicher.

## Kostenrahmen für den ersten kleinen Pilot

Der vorhandene Microsoft-Account ist nur die Anmeldung; Azure-Ressourcen werden
nach Verbrauch abgerechnet. Neue Azure-Kunden können einmalig ein
Startguthaben erhalten.

Als Arbeitsbudget, nicht als Microsoft-Angebot:

- **gemeinsamer kleiner Pilot:** ungefähr 20–80 EUR pro Monat
- **isolierter Pilot je Kunde:** ungefähr 50–200 EUR pro Monat
- **vollständig private Enterprise-Umgebung:** ab ungefähr 200 EUR pro Monat,
  abhängig von Netzwerk, Hochverfügbarkeit und Datenbank
- **LLM-Nutzung:** bei kleinen Controlling-Berichten meist nur wenige Euro; die
  ständig reservierte Infrastruktur ist normalerweise der größere Kostenblock

Die genaue Kalkulation wird vor jedem Deployment im Azure Pricing Calculator
für Region, Modell, Datenmenge und Sicherheitsprofil gespeichert. Offizielle
Quellen:

- [Azure-Konto und Startguthaben](https://azure.microsoft.com/pricing/purchase-options/azure-account)
- [Azure Container Apps](https://azure.microsoft.com/pricing/details/container-apps/)
- [Microsoft Foundry Models](https://azure.microsoft.com/pricing/details/ai-foundry-models/microsoft/)
- [Azure PostgreSQL Flexible Server](https://azure.microsoft.com/pricing/details/postgresql/flexible-server/)

## Migration bestehender Agenten

Alte Installationen mit nur `OPENAI_API_KEY` oder `ANTHROPIC_API_KEY` werden
nicht automatisch weitergeroutet. Vor dem Upgrade müssen `APP_ENV` und
`LLM_PROVIDER` ausdrücklich gesetzt werden. Das verhindert, dass ein
Kundenprompt unbemerkt die Vertrauensgrenze wechselt.
