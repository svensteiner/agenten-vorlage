/*
 * verify_pilot.js — Abnahmeprüfung der Pilot-Demo, ohne Browser.
 *
 * Zweck: die eine Frage beantworten, die vor jedem Kundentermin zählt —
 * "Steht irgendwo noch der Name des Vorkunden?" Ein einziger übersehener
 * Name ("Wer ist Krüger?") kostet den Termin, nicht nur die Stelle.
 *
 * Lädt pilot.config.js + data.js in einer VM-Sandbox mit window-Stub und prüft
 * beide Schalterstellungen. Ersetzt NICHT den Blick in den Browser (Layout,
 * Konsolenfehler, Streaming der geführten Demo) — es prüft die Daten, nicht die Optik.
 *
 * Aufruf aus dem Projektordner:
 *     node scripts/verify_pilot.js
 * Rückgabewert 0 = alles bestanden, 1 = mindestens eine Prüfung gerissen.
 */
const fs = require("fs");
const vm = require("vm");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const P = (f) => path.join(ROOT, "prototype", f);

// Quell-Identitäten der Meridian-Demo. Jede davon im Pilot-Zustand = Leak.
// ASCII-Varianten sind Absicht: Dateipfade schreiben Umlaute aus
// (gefunden 2026-08-17 in ".../MV-2024-003_Logistik_Nuernberg.pdf").
const LEAKS = [
  "Meridian", "meridian-industrie",
  "Vogel", "Krüger", "Krueger", "Brandt", "Reuter",
  "Elena Wagner", "Hoffmann", "Feldmann", "Petra Lang", "Sabine Reinhardt",
  "München", "Muenchen", "Ingolstadt", "Nürnberg", "Nuernberg",
];

const CONFIG_SRC = fs.readFileSync(P("pilot.config.js"), "utf8");
const DATA_SRC = fs.readFileSync(P("data.js"), "utf8");

/** Lädt Config + Daten in einer frischen Sandbox und gibt die Live-Werte zurück. */
function load(configSrc) {
  const sandbox = { window: {}, console };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(configSrc, sandbox, { filename: "pilot.config.js" });
  vm.runInContext(DATA_SRC, sandbox, { filename: "data.js" });
  // COMPANY/DOCS/... sind per const deklariert und landen daher nicht auf dem
  // Sandbox-Objekt — sie müssen im Kontext selbst ausgewertet werden.
  const g = (n) => vm.runInContext(n, sandbox);
  const parts = {
    COMPANY: g("COMPANY"),
    DOCS: g("DOCS"),
    SCENARIOS: g("SCENARIOS"),
    DECISION_CHAIN: g("typeof DECISION_CHAIN !== 'undefined' ? DECISION_CHAIN : null"),
  };
  return { cfg: sandbox.window.PILOT_CONFIG, ...parts, blob: JSON.stringify(parts) };
}

const results = [];
const ok = (name, cond, detail) => results.push({ name, pass: !!cond, detail });

// --- Zustand 1: Pilot scharf (der Auslieferungszustand) ---------------------
const on = load(CONFIG_SRC);
const docList = Object.values(on.DOCS);
const scenarioIds = new Set(on.SCENARIOS.map((s) => s.id));

ok("Schalter steht auf Pilot", on.cfg.active === true, `active=${on.cfg.active}`);
ok("Firmenname umgestellt", on.COMPANY.name === on.cfg.company.name, on.COMPANY.name);
ok("Logo-Glyph umgestellt", on.COMPANY.logoGlyph === on.cfg.company.logoGlyph, on.COMPANY.logoGlyph);
ok("Akzentfarbe gesetzt", !!on.COMPANY.accent, on.COMPANY.accent);

const leaked = LEAKS.filter((w) => on.blob.includes(w));
ok("0 Namensreste des Vorkunden", leaked.length === 0,
   leaked.length ? "GEFUNDEN: " + leaked.join(", ") : "keine");

ok("29 Dokumente unverändert", docList.length === 29, String(docList.length));
ok("17 Szenarien unverändert", on.SCENARIOS.length === 17, String(on.SCENARIOS.length));

// Die geführte Demo läuft über cfg.scenarios und hängt den Money-Shot an (app.js).
for (const id of on.cfg.scenarios) {
  ok(`Pilot-Szenario vorhanden: ${id}`, scenarioIds.has(id), scenarioIds.has(id) ? "ok" : "FEHLT");
}
ok("Money-Shot als Finale vorhanden", scenarioIds.has("agent-dazubuchen"),
   scenarioIds.has("agent-dazubuchen") ? "agent-dazubuchen" : "FEHLT");
ok("Genau 3 Pilot-Szenarien", on.cfg.scenarios.length === 3, String(on.cfg.scenarios.length));

// Belegpfade sind das, was der Kunde anklickt — sie müssen gefüllt sein.
const ohnePfad = docList.filter((d) => !d.path);
ok("jedes Dokument hat einen Belegpfad", ohnePfad.length === 0,
   ohnePfad.length ? ohnePfad.map((d) => d.id).join(", ") : "alle 29");

// Ein Beleg darf keinen Standort nennen, den die Firmenkarte nicht führt.
const factOrte = (on.COMPANY.facts || []).find((f) => /standort/i.test(f.label));
const orteKarte = factOrte ? factOrte.value : "";
const orteImKorpus = ["Augsburg", "Kempten"].filter((o) => on.blob.includes(o));
ok("Belegorte durch die Firmenkarte gedeckt",
   orteImKorpus.length > 0 && orteImKorpus.every((o) => orteKarte.includes(o)),
   `Karte: "${orteKarte}" · im Korpus: ${orteImKorpus.join(", ") || "keine"}`);

// --- Statisches HTML: darf keinen Firmennamen tragen ------------------------
// Der <title> steht im HTML und ist sichtbar, BEVOR app.js läuft. Ein Kundenname
// dort blitzt beim Laden im Browser-Tab auf — beim nächsten Piloten wäre es der
// Name des vorigen Kunden (gefunden 2026-08-17).
const HTML_SRC = fs.readFileSync(P("index.html"), "utf8");
const titleMatch = HTML_SRC.match(/<title>([^<]*)<\/title>/);
const staticTitle = titleMatch ? titleMatch[1].trim() : "";
ok("statischer <title> ohne Firmennamen",
   staticTitle === "AI Studio",
   staticTitle || "kein <title> gefunden");

// HTML-Kommentare werden ausgenommen: dort erklärt „Meridian" die interne
// Standarddemo (der Schaltzustand active:false) und ist kein Kundenname, der
// beim Umbau mitwandern müsste. Alles außerhalb von Kommentaren zählt.
const HTML_SICHTBAR = HTML_SRC.replace(/<!--[\s\S]*?-->/g, "");
const htmlLeaks = LEAKS.filter((w) => HTML_SICHTBAR.includes(w));
ok("index.html ohne Namensreste (außerhalb von Kommentaren)", htmlLeaks.length === 0,
   htmlLeaks.length ? "GEFUNDEN: " + htmlLeaks.join(", ") : "keine");

// Reihenfolge der Script-Tags: die Config MUSS vor data.js geladen werden,
// sonst greift der COMPANY-Guard dort ins Leere und das Umbranding bleibt aus.
const tagOrder = [...HTML_SRC.matchAll(/<script\s+src="([^"]+)"/g)].map((m) => m[1]);
ok("pilot.config.js wird vor data.js geladen",
   tagOrder.indexOf("pilot.config.js") >= 0 &&
     tagOrder.indexOf("pilot.config.js") < tagOrder.indexOf("data.js"),
   tagOrder.join(" → "));

// --- Replay-Pfad: answerCard muss existieren, sonst stirbt der Chat nach Modulwechsel ----
const APP_SRC = fs.readFileSync(P("app.js"), "utf8");
ok("function answerCard ist definiert",
   /function\s+answerCard\s*\(/.test(APP_SRC),
   /function\s+answerCard\s*\(/.test(APP_SRC) ? "ok" : "FEHLT in prototype/app.js");
ok("renderChatView ruft answerCard auf",
   /function\s+renderChatView\s*\(\s*\)[\s\S]*?answerCard\s*\(\s*m\.answer/.test(APP_SRC),
   /function\s+renderChatView\s*\(\s*\)[\s\S]*?answerCard\s*\(\s*m\.answer/.test(APP_SRC)
     ? "Call-Site in renderChatView"
     : "Call-Site in renderChatView fehlt");

// --- Zustand 2: Regressionsschutz (Schalter zurück auf die Standarddemo) ----
// Nur die Schalterzeile umlegen — nicht die Kommentare, die "active: true" erklären.
const OFF_SRC = CONFIG_SRC.replace("  active: true,", "  active: false,");
ok("Schalterzeile eindeutig gefunden", OFF_SRC !== CONFIG_SRC,
   OFF_SRC !== CONFIG_SRC ? "ok" : "Zeile '  active: true,' nicht gefunden");

const off = load(OFF_SRC);
ok("Schalter aus → Standarddemo zurück", off.COMPANY.name === "Meridian Industrie GmbH",
   off.COMPANY.name);
ok("Schalter aus → kein Pilotname im Korpus", !off.blob.includes(on.cfg.company.name),
   off.blob.includes(on.cfg.company.name) ? "LEAK" : "sauber");

// --- Ausgabe ---------------------------------------------------------------
let fail = 0;
for (const r of results) {
  if (!r.pass) fail++;
  console.log(`${r.pass ? "PASS" : "FAIL"}  ${r.name}${r.detail ? "  [" + r.detail + "]" : ""}`);
}
console.log(`\n${results.length - fail}/${results.length} bestanden` + (fail ? "  — NICHT vorführbereit" : "  — vorführbereit"));
process.exit(fail ? 1 : 0);
