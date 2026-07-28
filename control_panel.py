"""Local settings control panel for the automation-agent template.

A client-facing configuration surface: run this file, a browser opens with a
settings page. Change autonomy, models, limits, and behaviour flags without ever
touching JSON by hand. Saving validates the input and writes it back to
``config.json`` (runtime knobs) and syncs the autonomy fields into
``project/manifest.json`` so the governance layer stays consistent.

No third-party dependencies — Python standard library only.

    python control_panel.py            # serve on http://127.0.0.1:8770 and open browser
    python control_panel.py --port 9000 --no-browser

Design notes:
- SETTINGS_SPEC is the single source of truth for the UI *and* validation.
- Saving is immutable: we load the current config, build a new dict, then write.
- Security: binds to 127.0.0.1 only; writes are restricted to known keys.
"""

from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.json"
MANIFEST_PATH = ROOT / "project" / "manifest.json"
CONNECTORS_PATH = ROOT / "project" / "connectors.yaml"

# Destructive actions gated when autonomy_level is "gated".
DEFAULT_APPROVAL_ACTIONS = ["delete", "overwrite", "bulk changes", "external_send"]


# --- Settings specification -------------------------------------------------
# Each field: key, label (DE), type, help (DE), and type-specific options.
# type ∈ {"choice", "bool", "int", "text"}. This drives both rendering and
# validation so the two can never drift apart.
SETTINGS_SPEC: list[dict[str, Any]] = [
    {
        "key": "autonomy_level",
        "label": "Autonomie-Stufe",
        "type": "choice",
        "options": [
            ["gated", "Gated — Freigabe nötig (sicher, empfohlen)"],
            ["max", "Max — voll autonom, keine Freigabe"],
        ],
        "help": "Gated: destruktive/riskante Aktionen brauchen Freigabe (fail-closed). "
        "Max: der Agent führt alles selbst aus und protokolliert nur. "
        "Für Finance/HR/Legal wird 'Gated' empfohlen.",
        "group": "Sicherheit & Autonomie",
    },
    {
        "key": "model_provider",
        "label": "KI-Anbieter",
        "type": "choice",
        "options": [
            ["azure", "Azure (Standard)"],
            ["onprem", "Kunden-LLM / eigener Server"],
        ],
        "help": "Azure ist der Standard. Das Kunden-LLM nutzt einen privaten, "
        "OpenAI-kompatiblen Endpunkt in einer isolierten Kundenumgebung und "
        "fällt nicht automatisch auf Azure zurück.",
        "group": "Modell",
    },
    {
        "key": "quality_threshold",
        "label": "Qualitäts-Schwelle (1–10)",
        "type": "int",
        "min": 1,
        "max": 10,
        "help": "Wie streng die Ausgabe geprüft wird, bevor sie als fertig gilt.",
        "group": "Qualität & Verhalten",
    },
    {
        "key": "max_retries",
        "label": "Max. Wiederholungen",
        "type": "int",
        "min": 0,
        "max": 10,
        "help": "Wie oft der Agent bei zu niedriger Qualität nachbessert.",
        "group": "Qualität & Verhalten",
    },
    {
        "key": "loop_interval_minutes",
        "label": "Dauerlauf-Intervall (Minuten)",
        "type": "int",
        "min": 1,
        "max": 1440,
        "help": "Abstand zwischen zwei Durchläufen im Dauerlauf-Modus.",
        "group": "Qualität & Verhalten",
    },
    {
        "key": "max_actions_per_day",
        "label": "Max. Aktionen pro Tag",
        "type": "int",
        "min": 1,
        "max": 100000,
        "help": "Obergrenze gegen Kosten-/Aktions-Explosion (Rate-Limit).",
        "group": "Qualität & Verhalten",
    },
    {
        "key": "dry_run",
        "label": "Testmodus (dry-run)",
        "type": "bool",
        "help": "An: der Agent plant und zeigt Aktionen, führt aber nichts wirklich aus.",
        "group": "Qualität & Verhalten",
    },
    {
        "key": "proactive",
        "label": "Proaktiv",
        "type": "bool",
        "help": "An: der Agent schlägt von sich aus nächste Schritte vor.",
        "group": "Qualität & Verhalten",
    },
    {
        "key": "challenge_enabled",
        "label": "Selbst-Hinterfragen",
        "type": "bool",
        "help": "An: der Agent prüft seinen eigenen Plan kritisch, bevor er handelt.",
        "group": "Qualität & Verhalten",
    },
    {
        "key": "agent_name",
        "label": "Agent-Name",
        "type": "text",
        "help": "Anzeigename des Agenten.",
        "group": "Allgemein",
    },
]

SPEC_BY_KEY = {f["key"]: f for f in SETTINGS_SPEC}


# --- Config IO --------------------------------------------------------------
def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # fail loud, don't silently reset
        raise ValueError(f"{path.name} ist kein gültiges JSON: {exc}") from exc


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_settings() -> dict[str, Any]:
    """Return the current values for every spec field, derived from config.json."""
    config = _read_json(CONFIG_PATH)
    values: dict[str, Any] = {}
    for field in SETTINGS_SPEC:
        key = field["key"]
        if key == "model_provider":
            # Derived: which provider block is active.
            values[key] = config.get("model_provider", "azure")
        else:
            values[key] = config.get(key, _default_for(field))
    return values


def _default_for(field: dict[str, Any]) -> Any:
    if field["type"] == "bool":
        return False
    if field["type"] == "int":
        return field.get("min", 0)
    if field["type"] == "choice":
        return field["options"][0][0]
    return ""


def validate(incoming: dict[str, Any]) -> dict[str, Any]:
    """Validate raw form input against the spec. Raise ValueError on bad input."""
    clean: dict[str, Any] = {}
    for field in SETTINGS_SPEC:
        key = field["key"]
        if key not in incoming:
            continue
        raw = incoming[key]
        ftype = field["type"]
        if ftype == "choice":
            allowed = {opt[0] for opt in field["options"]}
            if raw not in allowed:
                raise ValueError(f"{field['label']}: '{raw}' ist keine gültige Option.")
            clean[key] = raw
        elif ftype == "bool":
            clean[key] = bool(raw)
        elif ftype == "int":
            try:
                num = int(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field['label']}: bitte eine ganze Zahl.") from exc
            lo, hi = field.get("min"), field.get("max")
            if lo is not None and num < lo:
                raise ValueError(f"{field['label']}: mindestens {lo}.")
            if hi is not None and num > hi:
                raise ValueError(f"{field['label']}: höchstens {hi}.")
            clean[key] = num
        else:  # text
            text = str(raw).strip()
            if not text:
                raise ValueError(f"{field['label']}: darf nicht leer sein.")
            clean[key] = text
    return clean


def save_settings(incoming: dict[str, Any]) -> dict[str, Any]:
    """Validate and persist settings. Returns the new value set.

    Writes runtime knobs to config.json and keeps the autonomy fields in
    project/manifest.json consistent so the governance layer agrees.
    """
    clean = validate(incoming)

    # Immutable update of config.json.
    config = dict(_read_json(CONFIG_PATH))
    config.update(clean)
    # Keep the legacy approval flag consistent with the autonomy level.
    if "autonomy_level" in clean:
        config["require_human_approval"] = clean["autonomy_level"] != "max"
    _write_json(CONFIG_PATH, config)

    # Sync autonomy into the project manifest (governance reads it there).
    if "autonomy_level" in clean and MANIFEST_PATH.exists():
        manifest = dict(_read_json(MANIFEST_PATH))
        level = clean["autonomy_level"]
        manifest["autonomy_level"] = level
        manifest["approval_required_for"] = [] if level == "max" else list(DEFAULT_APPROVAL_ACTIONS)
        _write_json(MANIFEST_PATH, manifest)

    return load_settings()


# --- Connectors (project/connectors.yaml) -----------------------------------
# The declared connector list IS the governance allowlist: only sources listed
# here may be used. Adding/removing here changes what the agent may reach.
def load_connectors() -> list[dict[str, str]]:
    if not CONNECTORS_PATH.exists():
        return []
    text = CONNECTORS_PATH.read_text(encoding="utf-8")
    try:
        import yaml

        data = yaml.safe_load(text) or {}
    except ImportError:
        return _parse_connectors_fallback(text)
    items = data.get("connectors") or []
    result = []
    for c in items:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        entry = {
            "name": str(c.get("name", "")).strip(),
            "url_env": str(c.get("url_env", "")).strip(),
            "description": str(c.get("description", "")).strip(),
        }
        # Preserve security-relevant fields the UI doesn't edit, so a UI save
        # never silently drops tool-scoping or required-ness.
        if "tools_enabled" in c:
            entry["tools_enabled"] = c["tools_enabled"]
        if "required" in c:
            entry["required"] = bool(c["required"])
        result.append(entry)
    return result


def _parse_connectors_fallback(text: str) -> list[dict[str, str]]:
    """Very small YAML reader for the connectors list when PyYAML is absent."""
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- name:"):
            if current:
                items.append(current)
            current = {"name": stripped.split(":", 1)[1].strip().strip("\"'"), "url_env": "", "description": ""}
        elif current is not None and ":" in stripped and not stripped.startswith("-"):
            key, _, val = stripped.partition(":")
            key = key.strip()
            if key in ("url_env", "description"):
                current[key] = val.strip().strip("\"'")
    if current:
        items.append(current)
    return items


def validate_connectors(items: Any) -> list[dict[str, str]]:
    if not isinstance(items, list):
        raise ValueError("Connectors müssen eine Liste sein.")
    clean: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Ungültiger Connector-Eintrag.")
        name = str(item.get("name", "")).strip()
        if not name:
            raise ValueError("Jeder Connector braucht einen Namen.")
        if name in seen:
            raise ValueError(f"Doppelter Connector-Name: '{name}'.")
        seen.add(name)
        entry = {
            "name": name,
            "url_env": str(item.get("url_env", "")).strip(),
            "description": str(item.get("description", "")).strip(),
        }
        if item.get("tools_enabled"):
            entry["tools_enabled"] = list(item["tools_enabled"])
        if "required" in item:
            entry["required"] = bool(item["required"])
        clean.append(entry)
    return clean


def save_connectors(items: Any) -> list[dict[str, str]]:
    clean = validate_connectors(items)
    CONNECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONNECTORS_PATH.write_text(_dump_connectors(clean), encoding="utf-8")
    return clean


def _dump_connectors(items: list[dict[str, str]]) -> str:
    header = (
        "# Declared external data sources (MCP servers / APIs).\n"
        "# This list is the governance allowlist — only connectors here may be used.\n"
        "# Managed via the settings UI (control_panel.py) or by hand.\n"
    )
    if not items:
        return header + "connectors: []\n"
    lines = [header, "connectors:"]
    for c in items:
        lines.append(f"  - name: {c['name']}")
        if c.get("url_env"):
            lines.append(f"    url_env: {c['url_env']}")
        if c.get("description"):
            lines.append(f"    description: \"{c['description']}\"")
        if c.get("tools_enabled"):
            tools = ", ".join(str(t) for t in c["tools_enabled"])
            lines.append(f"    tools_enabled: [{tools}]")
        if "required" in c:
            lines.append(f"    required: {str(c['required']).lower()}")
    return "\n".join(lines) + "\n"


# --- HTML rendering ---------------------------------------------------------
def render_page() -> str:
    return (
        _PAGE_TEMPLATE.replace("__SPEC__", json.dumps(SETTINGS_SPEC, ensure_ascii=False))
        .replace("__VALUES__", json.dumps(load_settings(), ensure_ascii=False))
        .replace("__CONNECTORS__", json.dumps(load_connectors(), ensure_ascii=False))
    )


_PAGE_TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent — Einstellungen</title>
<style>
  :root { --bg:#0f1420; --card:#171e2e; --line:#2a3550; --fg:#e7ecf5; --muted:#8f9bb5;
          --accent:#5b8cff; --warn:#ffcc66; --ok:#4ecb8f; --danger:#ff6b6b; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,Segoe UI,Roboto,sans-serif; background:var(--bg);
         color:var(--fg); line-height:1.5; }
  .wrap { max-width:760px; margin:0 auto; padding:32px 20px 80px; }
  h1 { font-size:1.5rem; margin:0 0 4px; }
  .sub { color:var(--muted); margin:0 0 28px; }
  .group { background:var(--card); border:1px solid var(--line); border-radius:14px;
           padding:20px 22px; margin-bottom:18px; }
  .group h2 { font-size:1rem; margin:0 0 16px; color:var(--accent); letter-spacing:.02em; }
  .field { padding:12px 0; border-top:1px solid var(--line); }
  .field:first-of-type { border-top:none; }
  .field label { font-weight:600; display:block; margin-bottom:4px; }
  .field .help { color:var(--muted); font-size:.86rem; margin-bottom:8px; }
  select, input[type=text], input[type=number] { width:100%; padding:9px 11px;
    background:#0c1120; color:var(--fg); border:1px solid var(--line); border-radius:9px; font-size:.95rem; }
  .toggle { display:inline-flex; align-items:center; gap:10px; cursor:pointer; }
  .toggle input { width:42px; height:24px; appearance:none; background:var(--line);
    border-radius:20px; position:relative; cursor:pointer; transition:.15s; }
  .toggle input:checked { background:var(--ok); }
  .toggle input::after { content:""; position:absolute; top:2px; left:2px; width:20px; height:20px;
    background:#fff; border-radius:50%; transition:.15s; }
  .toggle input:checked::after { left:20px; }
  .warn { display:none; margin-top:10px; padding:10px 12px; border-radius:9px;
    background:rgba(255,204,102,.12); border:1px solid var(--warn); color:var(--warn); font-size:.86rem; }
  .warn.show { display:block; }
  .bar { position:fixed; left:0; right:0; bottom:0; background:rgba(15,20,32,.95);
    border-top:1px solid var(--line); padding:14px 20px; display:flex; justify-content:center; gap:14px; align-items:center; }
  button { background:var(--accent); color:#fff; border:none; padding:11px 22px; border-radius:10px;
    font-size:.95rem; font-weight:600; cursor:pointer; }
  button.secondary { background:transparent; border:1px solid var(--line); color:var(--fg); }
  #status { min-height:20px; font-size:.9rem; }
  #status.ok { color:var(--ok); } #status.err { color:var(--danger); }
</style>
</head>
<body>
<div class="wrap">
  <h1>⚙️ Agent-Einstellungen</h1>
  <p class="sub">Konfiguriere den Agenten ohne Code. Änderungen werden in <code>config.json</code>
     und <code>project/manifest.json</code> gespeichert.</p>
  <form id="form"></form>

  <div class="group">
    <h2>Datenquellen (Connectors)</h2>
    <div class="help" style="margin-bottom:14px">Nur hier deklarierte Quellen darf der Agent
      nutzen (Allowlist). Das Secret kommt über die genannte Umgebungsvariable, nie im Klartext.</div>
    <div id="connectors"></div>
    <button type="button" class="secondary" style="margin-top:12px" onclick="addConnector()">+ Connector hinzufügen</button>
  </div>
</div>
<div class="bar">
  <span id="status"></span>
  <button type="button" class="secondary" onclick="location.reload()">Zurücksetzen</button>
  <button type="button" onclick="save()">Speichern</button>
</div>
<script>
const SPEC = __SPEC__;
const VALUES = __VALUES__;
let CONNECTORS = __CONNECTORS__;

function field(f) {
  const v = VALUES[f.key];
  let control;
  if (f.type === "choice") {
    control = `<select id="${f.key}">` + f.options.map(o =>
      `<option value="${o[0]}" ${o[0]===v?"selected":""}>${o[1]}</option>`).join("") + `</select>`;
  } else if (f.type === "bool") {
    control = `<label class="toggle"><input type="checkbox" id="${f.key}" ${v?"checked":""}><span></span></label>`;
  } else if (f.type === "int") {
    control = `<input type="number" id="${f.key}" value="${v}" min="${f.min??''}" max="${f.max??''}">`;
  } else {
    control = `<input type="text" id="${f.key}" value="${(v??'').toString().replace(/"/g,'&quot;')}">`;
  }
  const warn = f.key === "autonomy_level"
    ? `<div class="warn" id="warn_autonomy">⚠️ Voll-autonomer Modus: Der Agent führt auch löschende/überschreibende Aktionen ohne Freigabe aus. Nur für vertrauenswürdige, risikoarme Einsätze.</div>` : "";
  return `<div class="field"><label for="${f.key}">${f.label}</label>
    <div class="help">${f.help}</div>${control}${warn}</div>`;
}

function render() {
  const groups = {};
  SPEC.forEach(f => { (groups[f.group] ??= []).push(f); });
  document.getElementById("form").innerHTML = Object.entries(groups).map(([g, fields]) =>
    `<div class="group"><h2>${g}</h2>${fields.map(field).join("")}</div>`).join("");
  const sel = document.getElementById("autonomy_level");
  if (sel) { const upd = () => document.getElementById("warn_autonomy")
      .classList.toggle("show", sel.value === "max"); sel.addEventListener("change", upd); upd(); }
}

function collect() {
  const out = {};
  SPEC.forEach(f => {
    const el = document.getElementById(f.key);
    if (!el) return;
    if (f.type === "bool") out[f.key] = el.checked;
    else if (f.type === "int") out[f.key] = el.value;
    else out[f.key] = el.value;
  });
  return out;
}

function esc(s){ return (s??'').toString().replace(/"/g,'&quot;'); }

function renderConnectors() {
  const box = document.getElementById("connectors");
  if (!CONNECTORS.length) { box.innerHTML = `<div class="help">Noch keine Datenquellen deklariert.</div>`; return; }
  box.innerHTML = CONNECTORS.map((c, i) => `
    <div class="field" style="display:grid;grid-template-columns:1fr 1fr 40px;gap:8px;align-items:end">
      <div><label>Name</label><input type="text" value="${esc(c.name)}" oninput="CONNECTORS[${i}].name=this.value"></div>
      <div><label>Umgebungsvariable (url_env)</label><input type="text" value="${esc(c.url_env)}" oninput="CONNECTORS[${i}].url_env=this.value"></div>
      <button type="button" class="secondary" title="Entfernen" onclick="removeConnector(${i})">✕</button>
      <div style="grid-column:1/3"><label>Beschreibung</label><input type="text" value="${esc(c.description)}" oninput="CONNECTORS[${i}].description=this.value"></div>
    </div>`).join("");
}
function addConnector(){ CONNECTORS.push({name:"",url_env:"",description:""}); renderConnectors(); }
function removeConnector(i){ CONNECTORS.splice(i,1); renderConnectors(); }

async function save() {
  const status = document.getElementById("status");
  status.className = ""; status.textContent = "Speichere…";
  try {
    const res = await fetch("/api/config", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(collect())});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Unbekannter Fehler");
    Object.assign(VALUES, data.values);
    const cres = await fetch("/api/connectors", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({connectors: CONNECTORS})});
    const cdata = await cres.json();
    if (!cres.ok) throw new Error(cdata.error || "Connector-Fehler");
    CONNECTORS = cdata.connectors;
    renderConnectors();
    status.className = "ok"; status.textContent = "✓ Gespeichert";
  } catch (e) {
    status.className = "err"; status.textContent = "✗ " + e.message;
  }
}
render();
renderConnectors();
</script>
</body>
</html>
"""


# --- HTTP server ------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(200, render_page().encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/config":
            body = json.dumps({"values": load_settings()}, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        elif self.path == "/api/connectors":
            body = json.dumps({"connectors": load_connectors()}, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ("/api/config", "/api/connectors"):
            self._send(404, b"not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            incoming = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/connectors":
                connectors = save_connectors(incoming.get("connectors", []))
                body = json.dumps({"ok": True, "connectors": connectors}, ensure_ascii=False).encode("utf-8")
            else:
                values = save_settings(incoming)
                body = json.dumps({"ok": True, "values": values}, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        except ValueError as exc:
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self._send(400, body, "application/json; charset=utf-8")
        except Exception as exc:  # pragma: no cover - defensive
            body = json.dumps({"error": f"Serverfehler: {exc}"}, ensure_ascii=False).encode("utf-8")
            self._send(500, body, "application/json; charset=utf-8")

    def log_message(self, *args: Any) -> None:  # silence default logging
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent settings control panel")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"⚙️  Agent-Einstellungen laufen auf {url}")
    print("    (Fenster schließen oder Strg+C zum Beenden)")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
        server.shutdown()


if __name__ == "__main__":
    main()
