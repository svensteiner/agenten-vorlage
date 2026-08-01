# Lokale Controlling-Demo

Die Demo zeigt den vollständigen Weg aus Kundensicht:

1. Ein fiktives KMU bestellt den Demo-Agenten.
2. Eine eigene lokale Agenten-Instanz wird angelegt.
3. Die fest mitgelieferte Saldenliste und das Konten-Mapping werden anhand
   ihrer Prüfsummen kontrolliert.
4. Der Controlling-Bericht wird dreimal deterministisch erzeugt.
5. Nur bei drei übereinstimmenden, belegten Läufen wird das Management-Cockpit
   freigegeben.

## Start für eine Vorführung

Unter Windows genügt nach der einmaligen Voraussetzung ein Doppelklick auf
`START_CONTROLLING_DEMO.bat`. Der Launcher installiert bewusst nichts und bleibt
offline. Falls der freie XLSX-Reader fehlt, zeigt er diesen einmalig manuell
auszuführenden Befehl:
Alternativ:

```powershell
python -m pip install -r requirements-demo.txt
```

Danach startet die Demo ohne Netz- oder LLM-Zugriff:

```powershell
python order_portal.py
```

Danach öffnet sich `http://127.0.0.1:8765`. Für einen Test mit einem zufälligen
freien Port:

```powershell
python order_portal.py --port 0
```

Alle Laufdaten liegen unter `work/order-portal/` und werden nicht committet.

## Klare Grenzen

- Kostenbudget der Demo: exakt `0 EUR`
- ausschließlich synthetische Beispieldaten
- kein LLM- oder Azure-Aufruf
- keine Zahlung und kein Vertrag
- keine externe Aktion oder Nachricht
- nur auf `127.0.0.1` erreichbar
- lokale Pfadtrennung ist keine Produktions-Mandantentrennung

Für reale Kundendaten braucht jede Kundenumgebung den dokumentierten
Produktions-Sicherheitsnachweis. Azure wird später als Betriebsumgebung hinter
denselben Bestell- und Prüfvertrag gesetzt; die lokale Demo aktiviert Azure
nicht.

## Automatischer End-to-End-Test

```powershell
python -m pytest -q tests/e2e/test_order_portal_e2e.py
```

Der Test startet einen echten lokalen Server und Chromium, bestellt den Agenten,
führt die drei Kontrollläufe aus und öffnet den tatsächlich erzeugten Bericht.
Jeder nicht-lokale Browserzugriff wird dabei blockiert.
