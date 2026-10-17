# Strikte Schreibrechte fuer autonome Agenten

Eine Aufgabenbeschreibung begrenzt keine Dateirechte. Im nachgewiesenen Integrationslauf hat der Planer eine eingefrorene Testdatei selbst freigegeben; der Reviewer hat diese Entscheidung akzeptiert. Der externe Hostvergleich hat den Verstoss erkannt. [Originalauftrag und Belege](evidence/source-faithfulness-integration-20261017/README.md).

Die optionale Python-API `WritePolicy` legt genaue, relative Dateipfade beim Host fest. Das Modell kann diese Liste weder durch Aufgaben- noch durch Rollen- oder Reviewtexte erweitern. Jeder Eintrag bezeichnet genau eine Datei; es gibt keine Glob-Auswertung.

```python
from pathlib import Path
from agentkit.backends import CodexBackend
from agentkit.engine import Engine
from agentkit.write_policy import WritePolicy

engine = Engine(
    Path("agents/coding"),
    Path("workspaces/isolated-project"),
    CodexBackend("gpt-6-luna"),
    write_policy=WritePolicy(["src/agent.py"]),
    require_approvals=True,
)
engine.run("Verbessere src/agent.py und belege die Aenderung.")
```

Die Policy wird vor einer Schreibaktion, einer Freigabeanfrage und erneut an der Host-Schreibgrenze geprueft. Dateialiasse, Links/Junctions, mehrfach verlinkte Dateien, Traversal und interne Laufzeitpfade sind gesperrt. Der Policy-Hash bleibt an Lauf und offene Freigaben gebunden. Ein Wiederaufnehmen mit geaenderten Rechten scheitert. Neue Rechte erfordern einen neuen, ausdruecklich vom Host konfigurierten Auftrag.

Im strikten Codex-Modus arbeitet das Modell mit read-only Zugriff und liefert konkrete Schreibvorschlaege. Der Host fuehrt nur erlaubte Vorschlaege aus. Bei `require_approvals=True` ist die menschliche Zustimmung eine zusaetzliche Schranke; die Dateiliste ersetzt sie nicht. Bei False koennen erlaubte Vorschlaege autonom ausgefuehrt werden. DeepSeek prueft dieselben Rechte vor seinen Dateiwerkzeugen und bei wiederaufgenommenen/batchweisen Aktionen. Modellrouting ist nur moeglich, wenn alle konfigurierten Backends die Policy unterstuetzen und ihre gebundene Provideradresse erhalten.

`run_pytest` und beliebige Projektausfuehrung sind unter dieser strikten Policy gesperrt: Testcode koennte selbst beliebige Dateien schreiben. Der Host muss Tests getrennt mit einer geeigneten Ausfuehrungsgrenze veranlassen. Diese Policy ist keine Betriebssystem-Sandbox und schuetzt nicht vor einem anderen gleichzeitig schreibenden, privilegierten Hostprozess oder einem boesartigen selbst eingebundenen Python-Backend/Callback.

Ohne `write_policy` bleibt das bisherige Verhalten erhalten. CLI und Cockpit aktivieren die neue Dateiliste noch nicht automatisch; ihre bisherigen Aktionsfreigaben bleiben bestehen. Die neue Policy allein ist weder ein Nachweis vollstaendig autonomen Codings noch eine Produktionsfreigabe. Separate Lauf-/Review-/Test-/Modellqualitaetsnachweise bleiben erforderlich.
