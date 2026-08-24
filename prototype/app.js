/*
 * AI Studio Demo — Interaktionslogik.
 * Reines Vanilla-JS, keine Abhängigkeiten, läuft per Doppelklick (file://).
 * Rendert Chat, gestreamte Antworten, Quellen und den Dokumentenviewer.
 * Datenquelle: data.js (COMPANY, MODULES, DOCS, SCENARIOS, AGENT_CATALOG).
 */
(function () {
  "use strict";

  const $ = (sel, root) => (root || document).querySelector(sel);
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  let currentModule = "wissen";
  const chatState = []; // Verlauf, damit ein Modulwechsel den Chat nicht zerstört

  // „Geführte Demo": spielt eine kuratierte Kern-Auswahl der Szenarien hands-free ab.
  // token: monoton steigend; ein Stopp erhöht ihn und lässt laufende Schleifen aussteigen.
  const demo = { running: false, token: 0 };

  // Kuratierte Kern-Reihenfolge der Geführten Demo (Phase A: ≤ 4 min, je Szenario ≤ 25 s).
  // Bewusst eine Untermenge der SCENARIOS — ein straffer Story-Bogen fürs Verkaufsvideo, der
  // IMMER mit dem Money-Shot „Agenten dazubuchen" endet. Alle übrigen Szenarien bleiben per
  // Kachel/Frage/Suche erreichbar; nur die hands-free-Vorführung ist kuratiert.
  const MONEY_SHOT_ID = "agent-dazubuchen";
  const DEMO_ORDER = [
    "materialkosten",      // belegte Antwort · Quellen · Konfidenz · E-Mail aus dem Postfach
    "beleg-rechnung",      // Drei-Wege-Abgleich · prüfungsechte Rechnungsprüfung
    "budget-herkunft",     // Entscheidungskette als sichtbarer Beleg-Pfad (der CFO-Wow-Moment)
    "projekt-portfolio",   // Ampel Alpha + Beta · Breite + ehrliche Risiko-Kennzeichnung
    "strategie-ausblick",  // Governance: „weitere Treffer für Sie nicht freigegeben"
    MONEY_SHOT_ID,         // MONEY-SHOT · Finale · verkauft das Agenten-Abo
  ];

  // Löst DEMO_ORDER zu echten Szenario-Objekten auf: unbekannte/doppelte IDs werden
  // übersprungen (fail-safe), der Money-Shot steht garantiert am Ende (Video-Finale),
  // und falls die Kuratierung leer liefe, fällt sie sicher auf die volle SCENARIOS-Liste zurück.
  function demoScenarios() {
    const seen = new Set();
    const list = [];
    DEMO_ORDER.forEach((id) => {
      if (id === MONEY_SHOT_ID || seen.has(id)) return;
      const s = SCENARIOS.find((x) => x.id === id);
      if (s) { list.push(s); seen.add(id); }
    });
    const money = SCENARIOS.find((x) => x.id === MONEY_SHOT_ID);
    if (money) list.push(money);
    return list.length ? list : SCENARIOS.slice();
  }

  // ---------- Mietflotte (digitale Mitarbeiter) ----------
  // Persistente Miete: der Money-Shot und das Modul „Team" teilen denselben Stand.
  // Reset setzt auf den Auskunfts-Agenten (inklusive) zurück.
  const FLEET_KEY = "aistudio.fleet.v1";
  const teamUi = { tab: "fleet", filter: "alle", detailId: null, workId: null, workOut: null };
  let fleet = { leases: {} };

  function defaultFleet() {
    const leases = {};
    (typeof AGENT_CATALOG !== "undefined" ? AGENT_CATALOG : []).forEach((a) => {
      if (a.included) leases[a.id] = { status: "active", since: "inklusive", included: true };
    });
    return { leases };
  }

  function loadFleet() {
    let f = defaultFleet();
    try {
      const raw = localStorage.getItem(FLEET_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && parsed.leases && typeof parsed.leases === "object") f = parsed;
      }
    } catch (e) { /* file:// ohne Storage */ }
    const known = new Set((typeof AGENT_CATALOG !== "undefined" ? AGENT_CATALOG : []).map((a) => a.id));
    Object.keys(f.leases || {}).forEach((id) => { if (!known.has(id)) delete f.leases[id]; });
    (typeof AGENT_CATALOG !== "undefined" ? AGENT_CATALOG : []).forEach((a) => {
      if (a.included && !(f.leases && f.leases[a.id])) {
        f.leases = f.leases || {};
        f.leases[a.id] = { status: "active", since: "inklusive", included: true };
      }
    });
    return f;
  }

  function saveFleet() {
    try { localStorage.setItem(FLEET_KEY, JSON.stringify(fleet)); } catch (e) { /* ignore */ }
  }

  function resetFleet() {
    if (isLive()) {
      return AISTUDIO.fleetAction("", "reset").then((state) => {
        fleet = state;
        teamUi.tab = "fleet";
        teamUi.filter = "alle";
        teamUi.detailId = null;
        teamUi.workId = null;
        teamUi.workOut = null;
      });
    }
    fleet = defaultFleet();
    saveFleet();
    teamUi.tab = "fleet";
    teamUi.filter = "alle";
    teamUi.detailId = null;
    teamUi.workId = null;
    teamUi.workOut = null;
    return Promise.resolve();
  }

  function catalogById(id) {
    return (typeof AGENT_CATALOG !== "undefined" ? AGENT_CATALOG : []).find((a) => a.id === id) || null;
  }

  function leaseOf(id) { return (fleet.leases || {})[id] || null; }

  function isActive(id) {
    const a = catalogById(id);
    if (a && a.included) return true;
    const l = leaseOf(id);
    return !!(l && l.status === "active");
  }

  function isRented(id) {
    const a = catalogById(id);
    if (a && a.included) return true;
    const l = leaseOf(id);
    return !!(l && (l.status === "active" || l.status === "paused"));
  }

  function activeAgents() {
    return (typeof AGENT_CATALOG !== "undefined" ? AGENT_CATALOG : []).filter((a) => isActive(a.id));
  }

  function monthlyTotal() {
    return activeAgents().reduce((s, a) => s + (a.included ? 0 : (Number(a.price) || 0)), 0);
  }

  function formatEur(n) { return Number(n).toLocaleString("de-DE") + " €"; }

  function agentPriceLabel(a) {
    if (!a) return "";
    if (a.included || a.price === 0 || a.price === "inklusive") return "inklusive";
    if (typeof a.price === "string") return a.price;
    return formatEur(a.price);
  }

  function isLive() {
    return !!(window.AISTUDIO && AISTUDIO.isLive && AISTUDIO.isLive());
  }

  function todayGermanShort() {
    try { return new Date().toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }); }
    catch (e) { return "24.08.2026"; }
  }

  function nextInvoiceGerman() {
    try {
      const d = new Date();
      return new Date(d.getFullYear(), d.getMonth() + 1, 1)
        .toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
    } catch (e) { return "01.09.2026"; }
  }

  function rentAgent(id) {
    const a = catalogById(id);
    if (!a || a.included) return Promise.resolve(a);
    if (isLive()) {
      return AISTUDIO.fleetAction(id, "rent").then((state) => {
        fleet = state;
        return a;
      });
    }
    fleet.leases = fleet.leases || {};
    fleet.leases[id] = { status: "active", since: todayGermanShort(), included: false };
    saveFleet();
    return Promise.resolve(a);
  }

  function togglePause(id) {
    const l = leaseOf(id);
    if (!l || l.included) return Promise.resolve();
    if (isLive()) {
      const action = l.status === "paused" ? "resume" : "pause";
      return AISTUDIO.fleetAction(id, action).then((state) => { fleet = state; });
    }
    l.status = l.status === "paused" ? "active" : "paused";
    saveFleet();
    return Promise.resolve();
  }

  function cancelAgent(id) {
    const l = leaseOf(id);
    if (!l || l.included) return Promise.resolve();
    if (isLive()) {
      return AISTUDIO.fleetAction(id, "cancel").then((state) => {
        fleet = state;
        if (teamUi.workId === id) { teamUi.workId = null; teamUi.workOut = null; }
      });
    }
    delete fleet.leases[id];
    saveFleet();
    if (teamUi.workId === id) { teamUi.workId = null; teamUi.workOut = null; }
    return Promise.resolve();
  }

  function paidCount() {
    return activeAgents().filter((a) => !a.included).length;
  }

  // ---------- Dokument-Skins ----------
  // Papier-Anmutung (Briefkopf, Beleg-Stempel, Unterschriftszeile).
  const DOC_SKINS = {
    "Eingangsrechnung":     { cat: "beleg", extIssuer: true, stamp: { text: "EINGANG", tone: "ink" } },
    "Bestellung":           { cat: "beleg", stamp: { text: "GENEHMIGT", tone: "ok" } },
    "Wareneingang":         { cat: "beleg", stamp: { text: "GEPRÜFT", tone: "ok" } },
    "Rahmenvertrag":        { cat: "vertrag", sign: true },
    "Wartungsvertrag":      { cat: "vertrag", sign: true },
    "Lizenzvertrag":        { cat: "vertrag", sign: true },
    "Mietvertrag":          { cat: "vertrag", sign: true },
    "Richtlinie":           { cat: "richtlinie" },
    "Sicherheitsdokument":  { cat: "richtlinie" },
    "Prüfnachweis":         { cat: "nachweis", stamp: { text: "BESTANDEN", tone: "ok" } },
    "Mängelrüge":           { cat: "beleg", stamp: { text: "MÄNGELRÜGE", tone: "warn" } },
    "Gutschrift":           { cat: "beleg", extIssuer: true, stamp: { text: "GUTSCHRIFT", tone: "ok" } },
    "Nachtragsangebot":     { cat: "beleg", stamp: { text: "NACHTRAG", tone: "ink" } },
    "Auftragsbestätigung":  { cat: "beleg", extIssuer: true, stamp: { text: "BEAUFTRAGT", tone: "ok" } },
    "E-Mail":               { cat: "email" },
  };
  const defaultSkin = { cat: "bericht" };

  // ---------- Bootstrapping ----------
  async function init() {
    if (window.AISTUDIO && typeof AISTUDIO.boot === "function") {
      await AISTUDIO.boot();
    }
    fleet = (isLive() && AISTUDIO.fleet) ? AISTUDIO.fleet : loadFleet();
    renderSidebar();
    renderCompanyCard();
    selectModule("wissen");
    wireComposer();
    wireViewer();
    wireDemo();
    wireReset();
    wireSearch();
    wireOnboarding();
    wireRentOverlay();
    if (isLive()) {
      const st = $(".status");
      if (st) {
        const who = (AISTUDIO.user && AISTUDIO.user.name) ? AISTUDIO.user.name : "";
        st.classList.add("status-live");
        st.innerHTML = `<span class="dot"></span> Live · Wissensbasis verbunden` +
          (who ? `<span class="user-chip">${escapeHtml(who)}</span>` : "") +
          `<button class="reset-btn" type="button" id="logoutBtn" title="Abmelden" style="margin-left:8px"><span class="rl">Abmelden</span></button>`;
        const lo = $("#logoutBtn");
        if (lo) lo.onclick = () => AISTUDIO.logout();
      }
    }
  }

  // ---------- Onboarding-Coachmark (nur beim ersten Start) ----------
  // Zeigt beim ersten Laden ein leichtgewichtiges Overlay, das auf die
  // „Geführte Demo" zeigt. localStorage-Flag → erscheint nur einmal.
  const ONBOARD_KEY = "aistudio.onboarded.v1";
  function wireOnboarding() {
    const ob = $("#onboard");
    if (!ob) return;

    let seen = false;
    try { seen = localStorage.getItem(ONBOARD_KEY) === "1"; } catch (e) { seen = false; }
    if (seen) return; // schon gesehen → nicht mehr zeigen

    // Anzeigen und den Demo-Button dezent pulsieren lassen.
    ob.hidden = false;
    $("#demoBtn").classList.add("hi");

    const dismiss = () => {
      if (ob.hidden) return;
      ob.hidden = true;
      $("#demoBtn").classList.remove("hi");
      try { localStorage.setItem(ONBOARD_KEY, "1"); } catch (e) { /* file:// ohne Storage → einfach weiter */ }
    };

    $("#obSkip").onclick = dismiss;
    // Klick auf den abgedunkelten Hintergrund schließt ebenfalls.
    ob.addEventListener("click", (e) => { if (e.target === ob) dismiss(); });
    // Escape schließt.
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") dismiss(); });
    // Primär-CTA: schließen und direkt die Geführte Demo starten.
    $("#obStart").onclick = () => { dismiss(); startDemo(); };
  }

  // ---------- Geführte Demo (hands-free Auto-Play) ----------
  function wireDemo() {
    $("#demoBtn").onclick = () => (demo.running ? stopDemo() : startDemo());
  }

  async function startDemo() {
    if (demo.running) return;
    demo.running = true;
    const token = ++demo.token;

    const btn = $("#demoBtn");
    btn.classList.add("running");
    $(".di", btn).textContent = "⏹";
    $(".dl", btn).textContent = "Demo stoppen";
    const prog = $("#demoProgress");
    prog.hidden = false;
    $("#input").readOnly = true;

    // Frisch starten: zurück auf „Wissen", Verlauf leeren → Demo beginnt am Hero.
    chatState.length = 0;
    selectModule("wissen");
    await sleep(650);

    // Opener-Beat: die globale Suche als erstes Bild — „mein Unternehmen besitzt das alles bereits".
    if (token !== demo.token) return;
    await demoSearchBeat(token);
    if (token !== demo.token) return;

    const list = demoScenarios(); // kuratierte Kern-Auswahl, endet mit dem Money-Shot
    for (let i = 0; i < list.length; i++) {
      if (token !== demo.token) return;
      prog.textContent = `${i + 1} / ${list.length}`;
      await typeIntoComposer(list[i].question, token);
      if (token !== demo.token) return;
      await ask(list[i].question);
      if (token !== demo.token) return;
      // Letztes Szenario = Money-Shot: längere Schluss-Pause, damit sich der
      // empfohlene Agent hands-free selbst dazubucht (~1,25 s Wartezeit + ~0,9 s
      // Einrichtung) und die grüne „Aktiviert"-Bestätigung sichtbar stehen bleibt.
      await sleep(i === list.length - 1 ? 3400 : 2800); // Lesepause
    }
    if (token === demo.token) resetDemoUi();
  }

  function stopDemo() {
    demo.token++; // laufende Schleife steigt beim nächsten Check aus
    resetDemoUi();
  }

  function wireReset() {
    const btn = $("#resetBtn");
    if (btn) btn.onclick = resetDemo;
  }

  // Ein-Klick „Demo zurücksetzen": bringt die App in den sauberen Startzustand für
  // wiederholbare Video-Takes — laufende Demo sauber stoppen, Verlauf leeren, Viewer/
  // Palette schließen und zurück auf den Hero (Modul „Wissen"). Rein UI, kein Datenpfad.
  async function resetDemo() {
    if (demo.running) stopDemo(); else resetDemoUi();
    chatState.length = 0;
    closeViewer();
    closeSearch();
    closeRent();
    await resetFleet();
    hideFleetToast();
    selectModule("wissen");
  }

  function resetDemoUi() {
    demo.running = false;
    // Falls die Demo während des Such-Beats gestoppt wurde: Palette/Viewer sauber schließen.
    closeViewer();
    closeSearch();
    const btn = $("#demoBtn");
    btn.classList.remove("running");
    $(".di", btn).textContent = "▶";
    $(".dl", btn).textContent = "Geführte Demo";
    $("#demoProgress").hidden = true;
    const ta = $("#input");
    if (ta) { ta.readOnly = false; ta.value = ""; ta.style.height = "auto"; }
  }

  // Tippt die Frage sichtbar in den Composer (für die Video-Aufnahme).
  async function typeIntoComposer(text, token) {
    const ta = $("#input");
    ta.value = "";
    for (let i = 0; i < text.length; i++) {
      if (token !== demo.token) return;
      ta.value = text.slice(0, i + 1);
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
      await sleep(28);
    }
    await sleep(440);
    ta.value = "";
    ta.style.height = "auto";
  }

  // Opener-Beat der Geführten Demo: öffnet automatisch die Command-Palette, tippt
  // sichtbar „stahl", zeigt die Treffer quer über die Ressorts und öffnet kurz einen
  // Beleg — bevor die erste Frage läuft. Macht die schiere Menge des erschlossenen
  // Wissens zum ersten Bild des Videos. Rein choreografisch; nutzt die bestehenden
  // Such-/Viewer-Bausteine wieder und respektiert den token-Mechanismus + reduced-motion.
  async function demoSearchBeat(token) {
    const overlay = $("#searchOverlay");
    const input = $("#searchInput");
    if (!overlay || !input) return;
    const reduce = reducedMotion();

    // Palette öffnen (openSearch() ist während der Demo bewusst gesperrt → hier inline).
    search.open = true;
    overlay.hidden = false;
    input.value = "";
    renderSearchResults("");
    input.focus();
    await sleep(reduce ? 300 : 750); // „N Dokumente im Wissensspeicher" wirken lassen (Zähler dynamisch)
    if (token !== demo.token) return;

    // „stahl" sichtbar eintippen → live gefilterte Treffer quer über Finanzen + Audit.
    const query = "stahl";
    if (reduce) {
      input.value = query;
      renderSearchResults(query);
    } else {
      for (let i = 0; i < query.length; i++) {
        if (token !== demo.token) return;
        input.value = query.slice(0, i + 1);
        renderSearchResults(input.value);
        await sleep(95);
      }
    }
    await sleep(reduce ? 400 : 1000); // Trefferliste zeigen
    if (token !== demo.token) return;

    // Einen freigegebenen Beleg kurz öffnen (gesperrte übergehen → kein „Zugriff verweigert"
    // als Opener). Auswahl auf die geöffnete Zeile setzen, damit Highlight und Viewer passen.
    const idx = search.results.findIndex((d) => !d.locked);
    if (idx >= 0) {
      setSel(idx);
      await sleep(reduce ? 200 : 520);
      if (token !== demo.token) return;
      openViewer(search.results[idx].id);
      await sleep(reduce ? 500 : 1500); // Beleg lesen lassen
      if (token !== demo.token) return;
      closeViewer();
      await sleep(reduce ? 200 : 520);
    }
    if (token !== demo.token) return;

    closeSearch();
    await sleep(reduce ? 250 : 650);
  }

  // ---------- Sidebar ----------
  function renderSidebar() {
    const nav = $("#nav");
    nav.innerHTML = "";
    const groups = (typeof MODULE_GROUPS !== "undefined" && MODULE_GROUPS.length)
      ? MODULE_GROUPS
      : [{ label: "Module", keys: MODULES.map((m) => m.key) }];
    groups.forEach((g) => {
      nav.appendChild(el("div", "nav-label", g.label));
      g.keys.forEach((key) => {
        const m = MODULES.find((x) => x.key === key);
        if (!m) return;
        const count = m.key === "team" ? paidCount() : 0;
        const badge = count ? `<span class="nav-count">${count}</span>` : "";
        const btn = el("button", "nav-item", `<span class="ic">${m.icon}</span><span>${m.label}</span>${badge}`);
        btn.dataset.key = m.key;
        btn.onclick = () => selectModule(m.key);
        nav.appendChild(btn);
      });
    });
  }

  function refreshNavCounts() {
    const key = currentModule;
    renderSidebar();
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.key === key));
  }

  function renderCompanyCard() {
    const c = $("#companyCard");
    const rows = COMPANY.facts
      .map((f) => `<div class="row"><span>${f.label}</span><span>${f.value}</span></div>`)
      .join("");
    c.innerHTML =
      `<h4>${COMPANY.name}</h4>${rows}` +
      `<div class="demo-badge">● Demo-Daten · rein fiktiv</div>`;
  }

  function selectModule(key) {
    currentModule = key;
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.key === key));
    const mod = MODULES.find((m) => m.key === key);
    $("#topTitle").innerHTML = `${mod.label}<small>${mod.hint}</small>`;

    if (key === "wissen") return renderChatView();
    if (key === "team") return renderTeamView();
    if (key === "einstellungen") return renderSettingsView();
    return renderLibraryView(key);
  }

  // ---------- Chat-Ansicht ----------
  function renderChatView() {
    const scroll = $("#scroll");
    scroll.innerHTML = "";
    const wrap = el("div", "wrap");
    wrap.id = "chatWrap";
    scroll.appendChild(wrap);
    $("#composer").style.display = "";

    if (chatState.length === 0) {
      renderHero(wrap);
    } else {
      chatState.forEach((m) => {
        if (m.role === "user") wrap.appendChild(userBubble(m.text));
        else wrap.appendChild(answerCard(m.answer, m.question));
      });
      scrollBottom();
    }
  }

  function renderHero(wrap) {
    const hero = el("div", "hero");
    hero.innerHTML =
      `<div class="spark">✦</div>` +
      `<h1>Ihr Unternehmenswissen — sofort abrufbar</h1>` +
      `<p>Stellen Sie eine Frage in natürlicher Sprache. AI Studio durchsucht Verträge, Rechnungen, Berichte und Richtlinien der ${COMPANY.name} und antwortet mit belastbaren Quellen.</p>`;
    wrap.appendChild(hero);

    const grid = el("div", "suggestions");
    (MODULE_SUGGESTIONS.wissen || []).forEach((sid) => {
      const s = SCENARIOS.find((x) => x.id === sid);
      if (!s) return;
      const mod = MODULES.find((m) => m.key === s.module);
      const card = el("button", "suggest-card",
        `<div class="q">${s.question}</div><span class="tag">${mod ? mod.label : ""}</span>`);
      card.onclick = () => ask(s.question);
      grid.appendChild(card);
    });
    wrap.appendChild(grid);
  }

  // ---------- Frage stellen ----------
  async function ask(text) {
    text = (text || "").trim();
    if (!text) return;

    // Direkte Sprünge in die Mietplattform (nicht der Money-Shot-Chat).
    if (isTeamJump(text)) {
      const q = text.toLowerCase();
      teamUi.tab = /marktplatz|agenten mieten|mieten/.test(q) ? "market"
        : /abrechnung|rechnung/.test(q) ? "billing"
        : /auftrag/.test(q) ? "work"
        : "fleet";
      selectModule("team");
      return;
    }

    // Falls der Hero noch da ist: Chat-Ansicht in „aktiven" Modus versetzen
    if (currentModule !== "wissen") selectModule("wissen");
    const wrap = $("#chatWrap");
    const hero = $(".hero"); if (hero) hero.remove();
    const sugg = $(".suggestions"); if (sugg) sugg.remove();

    chatState.push({ role: "user", text });
    wrap.appendChild(userBubble(text));
    scrollBottom();

    const scenario = matchScenario(text);

    // „Denk"-Phase mit sichtbaren Retrieval-Schritten
    const thinking = el("div", "msg");
    const t = el("div", "thinking", `<span class="spinner"></span><span class="steps">Durchsuche Wissensbasis…</span>`);
    thinking.appendChild(t);
    wrap.appendChild(thinking);
    scrollBottom();

    const steps = scenario
      ? ["Durchsuche Wissensbasis…", "Prüfe Zugriffsrechte…", "Werte relevante Dokumente aus…", "Formuliere Antwort mit Quellen…"]
      : ["Durchsuche Wissensbasis…", "Prüfe Zugriffsrechte…", "Werte Treffer aus…"];
    for (const s of steps) {
      $(".steps", t).textContent = s;
      await sleep(360);
    }
    thinking.remove();

    if (demo.running) {
      if (scenario) {
        chatState.push({ role: "ai", answer: scenario.answer, question: text });
        await streamAnswer(wrap, scenario.answer);
      } else {
        const fallback = fallbackAnswer(text);
        chatState.push({ role: "ai", answer: fallback, question: text });
        await streamAnswer(wrap, fallback);
      }
      return;
    }

    if (isLive()) {
      try {
        const answer = await AISTUDIO.ask(text);
        chatState.push({ role: "ai", answer: answer, question: text });
        await streamAnswer(wrap, answer);
      } catch (e) {
        const fallback = fallbackAnswer(text);
        fallback.reasoning = (fallback.reasoning || []).concat(["Live-Suche nicht erreichbar — lokale Demo-Antwort."]);
        chatState.push({ role: "ai", answer: fallback, question: text });
        await streamAnswer(wrap, fallback);
      }
      return;
    }

    if (scenario) {
      chatState.push({ role: "ai", answer: scenario.answer, question: text });
      await streamAnswer(wrap, scenario.answer);
    } else {
      const fallback = fallbackAnswer(text);
      chatState.push({ role: "ai", answer: fallback, question: text });
      await streamAnswer(wrap, fallback);
    }
  }

  function userBubble(text) {
    const m = el("div", "msg user");
    m.appendChild(el("div", "bubble", escapeHtml(text)));
    return m;
  }

  // ---------- Konfidenz-Herleitung ----------
  // Macht die Prozentzahl im Antwortkopf greifbar: sie ist keine Behauptung,
  // sondern eine Ableitung aus den herangezogenen Quellen — Anzahl, höchste
  // Relevanz und Grad der Übereinstimmung der Belege. Rein datengetrieben aus
  // answer.sources (keine neuen Datenfelder); ohne Quellen (Fallback-Antwort)
  // erscheint kein Tooltip. Entkräftet den letzten CFO-Einwand „woher weiß das
  // System das?" direkt am Meter (Cursor hovert → Zahl wird erklärt).
  function buildConfPop(answer) {
    const sources = (answer.sources || []).filter((s) => DOCS[s.docId]);
    if (!sources.length) return "";
    const rels = sources.map((s) => s.relevance).sort((a, b) => b - a);
    const n = sources.length;
    const top = rels[0];
    const strong = rels.filter((r) => r >= 80).length;
    let agreeVal, agreeSub, agreePct;
    if (n === 1) {
      agreeVal = "einzeln"; agreeSub = "eine belastbare Quelle"; agreePct = 55;
    } else if (strong >= 2) {
      agreeVal = "hoch"; agreeSub = strong + " von " + n + " Belegen ≥ 80 % Relevanz"; agreePct = 92;
    } else {
      agreeVal = "teilweise"; agreeSub = strong + " von " + n + " Belegen ≥ 80 % Relevanz"; agreePct = 70;
    }
    const nPct = (Math.min(n, 4) / 4) * 100;
    const row = (label, val, pct, sub) =>
      `<span class="cp-factor">` +
      `<span class="cp-line"><span class="cp-k">${label}</span><span class="cp-v">${val}</span></span>` +
      `<span class="cp-bar"><i style="width:${pct}%"></i></span>` +
      (sub ? `<span class="cp-sub">${sub}</span>` : "") +
      `</span>`;
    return `<span class="conf-pop" role="tooltip">` +
      `<span class="cp-title">So ergibt sich die <b>Konfidenz ${answer.confidence}%</b></span>` +
      row("Quellen herangezogen", n, nPct) +
      row("Höchste Relevanz", top + "%", top) +
      row("Übereinstimmung der Belege", agreeVal, agreePct, agreeSub) +
      `<span class="cp-foot">Keine Behauptung — eine Ableitung aus konkreten Quellen.</span>` +
      `</span>`;
  }

  // ---------- Antwort streamen ----------
  async function streamAnswer(wrap, answer) {
    const msg = el("div", "msg");
    const card = el("div", "answer");
    // Konfidenz nur zeigen, wenn die Antwort eine ist (Wissens-Lookup). Der
    // Money-Shot („Agenten dazubuchen") ist eine Buchungs-Ansicht ohne Quellen →
    // keine Konfidenzzahl, kein Herleitungs-Tooltip.
    const hasConf = typeof answer.confidence === "number";
    const confCls = answer.confidence >= 90 ? "" : "mid";
    // Kopf: „Beantwortet in X,X s"-Signal (Tempo) links vom Konfidenz-Meter.
    const secs = answerSeconds(answer);
    // Hover/Focus am Konfidenz-Meter erklärt, woraus sich die Prozentzahl speist.
    const pop = hasConf ? buildConfPop(answer) : "";
    const confHtml = hasConf
      ? `<span class="conf${pop ? " has-pop" : ""}"${pop ? ' tabindex="0" aria-label="Konfidenz — Herleitung anzeigen"' : ""}>` +
        `<span class="conf-meter">Konfidenz` +
        `<span class="conf-bar ${confCls}"><i style="width:${answer.confidence}%"></i></span>` +
        `<b>${answer.confidence}%</b>` +
        (pop ? `<span class="conf-i" aria-hidden="true">ⓘ</span>` : "") +
        `</span>${pop}</span>`
      : "";
    card.appendChild(el("div", "head",
      `<span class="ai">✦</span><span class="who">AI Studio</span>` +
      `<span class="speed" title="Antwortzeit">⚡ Beantwortet in <b class="sp-val">0,0 s</b></span>` +
      confHtml));
    const textEl = el("div", "text");
    textEl.classList.add("cursor");
    card.appendChild(textEl);
    msg.appendChild(card);
    wrap.appendChild(msg);
    scrollBottom();

    // Tempo-Signal sofort hochzählen — lässt das System „live" und schnell wirken.
    countUp($(".sp-val", card), secs, 1, " s");

    // Konfidenz-Meter „lebendig": die Zahl zählt hoch UND der Balken läuft von 0
    // auf den Zielwert mit (statt hart zu springen) — die letzte Bewegungs-Politur
    // im Antwortkopf. prefers-reduced-motion → beide sofort auf den Endwert.
    if (hasConf) {
      countUp($(".conf-meter > b", card), answer.confidence, 0, "%");
      animateBar($(".conf-bar i", card), 760);
      if (pop) wireConfPopBars(card);
    }

    // Text zeichenweise „tippen" (HTML-sicher: wir tippen den fertigen HTML-String schrittweise)
    await typeHtml(textEl, answer.text);
    textEl.classList.remove("cursor");

    // Kernzahlen in der Antwort dezent hochzählen (18,4 %, 87.584 €, -12,0 % …).
    animateCounts(textEl);

    // Danach die strukturierten Blöcke einblenden
    appendChain(card, answer.chain);
    appendReasoning(card, answer.reasoning);
    appendSources(card, answer.sources);
    appendWithheld(card, answer.withheld);
    appendRelated(card, answer.related);
    appendFollowups(card, answer.followups);
    appendActions(card, answer);
    appendAgents(card, answer);
    revealBlocks(card);
    scrollBottom();
  }

  // Replay vorhandener Chat-Antworten nach Modulwechsel (ohne Tipp-/Zähl-Animation).
  // Schließt den latenten Bug: renderChatView() rief answerCard(), die nicht existierte.
  function answerCard(answer) {
    const msg = el("div", "msg");
    const card = el("div", "answer");
    const hasConf = typeof answer.confidence === "number";
    const confCls = answer.confidence >= 90 ? "" : "mid";
    const secs = answerSeconds(answer);
    const pop = hasConf ? buildConfPop(answer) : "";
    const confHtml = hasConf
      ? `<span class="conf${pop ? " has-pop" : ""}"${pop ? ' tabindex="0" aria-label="Konfidenz — Herleitung anzeigen"' : ""}>` +
        `<span class="conf-meter">Konfidenz` +
        `<span class="conf-bar ${confCls}"><i style="width:${answer.confidence}%"></i></span>` +
        `<b>${answer.confidence}%</b>` +
        (pop ? `<span class="conf-i" aria-hidden="true">ⓘ</span>` : "") +
        `</span>${pop}</span>`
      : "";
    const secStr = String(secs).replace(".", ",");
    card.appendChild(el("div", "head",
      `<span class="ai">✦</span><span class="who">AI Studio</span>` +
      `<span class="speed" title="Antwortzeit">⚡ Beantwortet in <b class="sp-val">${secStr} s</b></span>` +
      confHtml));
    const textEl = el("div", "text");
    textEl.innerHTML = answer.text || "";
    card.appendChild(textEl);
    msg.appendChild(card);
    appendChain(card, answer.chain);
    appendReasoning(card, answer.reasoning);
    appendSources(card, answer.sources);
    appendWithheld(card, answer.withheld);
    appendRelated(card, answer.related);
    appendFollowups(card, answer.followups);
    appendActions(card, answer);
    appendAgents(card, answer);
    if (pop) wireConfPopBars(card);
    return msg;
  }

  // Lässt die strukturierten Blöcke (Nachvollziehbarkeit → Quellen → Verwandte →
  // Folgefragen → Aktionen) gestaffelt einblenden statt hart zu springen — die
  // Antwort baut sich souverän auf. Rein visuell: jeder Block bekommt eine kleine,
  // additive Verzögerung. `prefers-reduced-motion` deaktiviert die Animation (CSS).
  function revealBlocks(card) {
    if (reducedMotion()) return; // Blöcke stehen bereits sichtbar im DOM
    const blocks = card.querySelectorAll(".block");
    blocks.forEach((b, i) => {
      b.style.setProperty("--rev-delay", i * 55 + "ms");
      b.classList.add("reveal");
    });
  }

  // Plausible, deterministische Antwortzeit (keine Zufallszahl → im Video reproduzierbar).
  // Basiert auf Umfang der Antwort, bewusst im „schnell wirkenden" Fenster 1,2–2,6 s.
  function answerSeconds(answer) {
    let s = 1.2;
    s += (answer.sources ? answer.sources.length : 0) * 0.16;
    s += (answer.text || "").length / 2600;
    if (/<table/.test(answer.text || "")) s += 0.3;
    s = Math.max(1.2, Math.min(2.6, s));
    return Math.round(s * 10) / 10;
  }

  async function typeHtml(node, html) {
    // Tippt sichtbaren Text schrittweise; setzt am Ende das volle HTML.
    const plain = html.replace(/<[^>]+>/g, "");
    const chunk = Math.max(2, Math.round(plain.length / 60));
    let shown = "";
    for (let i = 0; i < plain.length; i += chunk) {
      shown = plain.slice(0, i + chunk);
      node.textContent = shown;
      scrollBottom();
      await sleep(16);
    }
    node.innerHTML = html;
  }

  function appendReasoning(card, reasoning) {
    if (!reasoning || !reasoning.length) return;
    const b = el("div", "block reasoning");
    b.appendChild(el("div", "block-title", "◈ Nachvollziehbarkeit"));
    const ol = el("ol");
    reasoning.forEach((r) => ol.appendChild(el("li", null, escapeHtml(r))));
    b.appendChild(ol);
    card.appendChild(b);
  }

  function appendSources(card, sources) {
    if (!sources || !sources.length) return;
    const b = el("div", "block");
    b.appendChild(el("div", "block-title", `◉ Quellen (${sources.length})`));
    sources.forEach((s) => {
      const doc = DOCS[s.docId];
      if (!doc) return;
      const row = el("div", "source");
      row.innerHTML =
        `<span class="ficon">▤</span>` +
        `<span class="meta"><span class="t">${doc.title}</span>` +
        `<span class="q">„${escapeHtml(s.quote)}"</span>` +
        `<span class="p">${doc.path}</span></span>` +
        `<span class="rel">Relevanz<b>${s.relevance}%</b></span>`;
      row.onclick = () => openViewer(s.docId, s.quote);
      b.appendChild(row);
    });
    card.appendChild(b);
  }

  // Governance-Signal: „N weitere Treffer für Sie nicht freigegeben".
  // Macht Berechtigungstreue in Sekunden greifbar (CFO/Compliance-Frage
  // „Sieht jeder alles?"). Die gesperrten Dokumente sind anklickbar und öffnen
  // die „Zugriff verweigert"-Ansicht.
  function appendWithheld(card, withheld) {
    if (!withheld || !withheld.count) return;
    const b = el("div", "block withheld");
    b.appendChild(el("div", "block-title", "🔒 Nicht freigegeben"));
    const head = el("div", "wh-head",
      `<b>${withheld.count} weitere Treffer</b> für Sie nicht freigegeben` +
      (withheld.role ? ` <span class="wh-tag">Klassifizierung: ${escapeHtml(withheld.role)}</span>` : ""));
    b.appendChild(head);
    if (withheld.note) b.appendChild(el("div", "wh-note", escapeHtml(withheld.note)));
    if (withheld.docs && withheld.docs.length) {
      const box = el("div", "wh-list");
      withheld.docs.forEach((id) => {
        const doc = DOCS[id];
        if (!doc) return;
        const row = el("button", "wh-item",
          `<span class="lk">🔒</span>` +
          `<span class="wt">${doc.title}<span class="wty">${escapeHtml(doc.type)}</span></span>` +
          `<span class="wr">Kein Zugriff</span>`);
        row.onclick = () => openViewer(id);
        box.appendChild(row);
      });
      b.appendChild(box);
    }
    card.appendChild(b);
  }

  // ---------- Beleg-Pfad / Entscheidungskette ----------
  // Zeigt die Herkunft einer Kernaussage als sichtbare Timeline quer durch
  // Postfächer und Gremien (Lieferant → Einkauf → CFO → Vorstand). Jeder Schritt
  // ist anklickbar und öffnet den zugehörigen Beleg im Viewer. Rein additiv,
  // datengetrieben aus answer.chain — analog zu appendWithheld(). Macht den
  // stärksten CFO-Moment (die ganze Entscheidungskette) ohne Klickarbeit sichtbar.
  function appendChain(card, chain) {
    if (!chain || !chain.steps || !chain.steps.length) return;
    const b = el("div", "block chain");
    b.appendChild(el("div", "block-title", "⛓ " + (chain.title || "Entscheidungskette")));
    const line = el("div", "chain-line");
    chain.steps.forEach((step) => {
      const doc = step.docId ? DOCS[step.docId] : null;
      const node = el("div", step.strong ? "chain-step strong" : "chain-step");
      node.innerHTML =
        `<span class="cs-dot"></span>` +
        `<div class="cs-body">` +
        `<div class="cs-head">` +
        `<span class="cs-date">${escapeHtml(step.date)}</span>` +
        `<span class="cs-actor">${escapeHtml(step.actor)}</span></div>` +
        `<div class="cs-label">${escapeHtml(step.label)}</div>` +
        (step.desc ? `<div class="cs-desc">${escapeHtml(step.desc)}</div>` : "") +
        (doc ? `<span class="cs-src">▤ ${escapeHtml(doc.title)}</span>` : "") +
        `</div>`;
      if (doc) { node.classList.add("clickable"); node.onclick = () => openViewer(step.docId); }
      line.appendChild(node);
    });
    b.appendChild(line);
    card.appendChild(b);
  }

  function appendRelated(card, related) {
    if (!related || !related.length) return;
    const b = el("div", "block");
    b.appendChild(el("div", "block-title", "⊞ Verwandte Dokumente"));
    const box = el("div", "related");
    related.forEach((id) => {
      const doc = DOCS[id];
      if (!doc) return;
      const pill = el("button", "pill", `▤ ${doc.title}`);
      pill.onclick = () => openViewer(id);
      box.appendChild(pill);
    });
    b.appendChild(box);
    card.appendChild(b);
  }

  function appendFollowups(card, followups) {
    if (!followups || !followups.length) return;
    const b = el("div", "block");
    b.appendChild(el("div", "block-title", "➜ Folgefragen"));
    const box = el("div", "chips");
    followups.forEach((q) => {
      const chip = el("button", "chip", q);
      chip.onclick = () => ask(q);
      box.appendChild(chip);
    });
    b.appendChild(box);
    card.appendChild(b);
  }

  // ---------- Handlungs-Abschluss ("und dann?") ----------
  // Macht aus der belegten Auskunft ein weiterreichbares Arbeitsergebnis:
  // ein Klick auf „An Vorstand senden" / „Als Briefing exportieren" zeigt eine
  // überzeugende Bestätigung. Rein UI — keine echten Mails/Exporte. Erscheint
  // nur bei belegten Antworten (mind. eine Quelle), nicht bei Leer-Fallbacks.
  function appendActions(card, answer) {
    if (!answer.sources || !answer.sources.length) return;
    const b = el("div", "block actions");
    b.appendChild(el("div", "block-title", "↗ Ergebnis weiterreichen"));
    const row = el("div", "act-row");
    const send = el("button", "act primary", `<span class="ai-ic">✉</span>An Vorstand senden`);
    const exp = el("button", "act", `<span class="ai-ic">⤓</span>Als Briefing exportieren`);
    row.appendChild(send);
    row.appendChild(exp);
    b.appendChild(row);
    card.appendChild(b);

    const num = briefingNumber(answer);
    send.onclick = () => runAction(row, "send", num);
    exp.onclick = () => runAction(row, "export", num);
  }

  // Deterministische Briefing-Nummer aus dem Antwortinhalt (im Video reproduzierbar,
  // keine Zufallszahl — konsistent mit dem Tempo-Signal aus Zyklus 8).
  function briefingNumber(answer) {
    const base = (answer.text || "") + "|" + (answer.confidence || 0);
    let h = 0;
    for (let i = 0; i < base.length; i++) h = (h * 31 + base.charCodeAt(i)) >>> 0;
    return 1000 + (h % 9000);
  }

  function todayGerman() {
    try {
      return new Date().toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" });
    } catch (e) { return "8. Juli 2026"; }
  }

  // Spielt die kurze Vorbereitungs-Animation ab und ersetzt die Buttons durch
  // eine Erfolgs-Bestätigung — der Schlussmoment der Demo-Story.
  async function runAction(row, kind, num) {
    const pending = kind === "send" ? "Briefing wird zusammengestellt…" : "PDF wird erzeugt…";
    row.innerHTML = `<span class="act-pending"><span class="spinner"></span>${pending}</span>`;
    await sleep(reducedMotion() ? 0 : 820);

    const done = el("div", "act-done");
    if (kind === "send") {
      done.innerHTML =
        `<span class="ok-badge">✓</span>` +
        `<span class="ad-txt"><b>Briefing an den Vorstand gesendet</b>` +
        `<span class="ad-sub">Empfänger: Vorstand · ${escapeHtml(COMPANY.name)} · soeben · Ref. BRF-2026-${num}</span></span>`;
    } else {
      done.innerHTML =
        `<span class="ok-badge">✓</span>` +
        `<span class="ad-txt"><b>Briefing als PDF exportiert</b>` +
        `<span class="ad-sub">meridian-briefing-2026-${num}.pdf · ${escapeHtml(todayGerman())}</span></span>`;
    }
    row.replaceWith(done);
    scrollBottom();
  }

  // ---------- Money-Shot: „Agenten dazubuchen" ----------
  // Der Abschluss der Story und der Verkaufsmoment des Abos: Die Wissensbasis
  // steht — jetzt mietet der Kunde spezialisierte KI-Agenten obendrauf, wie neue
  // Mitarbeiter, monatlich kündbar. Rein UI (keine echte Buchung). Datengetrieben
  // aus answer.agents; erscheint nur beim Money-Shot-Szenario. In der Geführten
  // Demo bucht sich der empfohlene Agent hands-free selbst — der Payoff im Video.
  function appendAgents(card, answer) {
    if (!answer.agents || !answer.agents.length) return;
    const b = el("div", "block agents");
    b.appendChild(el("div", "block-title", "🤝 Agenten dazubuchen — wie neue Mitarbeiter"));
    const grid = el("div", "agent-grid");
    answer.agents.forEach((a) => {
      const cat = a.id ? catalogById(a.id) : null;
      const live = cat ? isActive(cat.id) : !!a.active;
      const rec = !!(a.recommended || (cat && cat.recommended));
      const item = el("div", "agent-card" + (rec && !live ? " rec" : "") + (live ? " on" : ""));
      const badge = live
        ? `<span class="ag-badge active">● Aktiv</span>`
        : (rec ? `<span class="ag-badge rec">Empfohlen</span>` : "");
      const price = cat ? agentPriceLabel(cat) : (a.price || "");
      item.innerHTML =
        `<div class="ag-top">` +
        `<span class="ag-ic">${a.icon || (cat && cat.icon) || "✦"}</span>` +
        `<span class="ag-h"><span class="ag-name">${escapeHtml(a.name)}</span>` +
        `<span class="ag-role">${escapeHtml(a.role)}</span></span>` +
        badge +
        `</div>` +
        `<div class="ag-desc">${escapeHtml(a.desc)}</div>` +
        `<div class="ag-foot"><span class="ag-price">${escapeHtml(price)}` +
        (live || price === "inklusive" ? `` : `<span class="ag-per"> / Monat</span>`) + `</span></div>`;
      const foot = $(".ag-foot", item);
      if (!live) {
        const btn = el("button", "ag-book", `<span class="ag-plus">＋</span>Dazubuchen`);
        btn.onclick = () => bookAgent(item, a);
        foot.appendChild(btn);
      } else {
        foot.insertAdjacentHTML("beforeend", `<span class="ag-live">✓ Teil Ihres Teams</span>`);
      }
      grid.appendChild(item);
    });
    b.appendChild(grid);
    if (answer.priceNote) b.appendChild(el("div", "ag-note", escapeHtml(answer.priceNote)));
    if (!demo.running) {
      const more = el("button", "btn ghost");
      more.style.margin = "12px auto 0";
      more.style.display = "flex";
      more.textContent = "Alle Agenten im Modul Team →";
      more.onclick = () => { teamUi.tab = "market"; selectModule("team"); };
      b.appendChild(more);
    }
    card.appendChild(b);

    // Hands-free-Payoff: In der Geführten Demo bucht sich der empfohlene Agent
    // nach einer kurzen Lesepause selbst → der „dazubuchen"-Moment ist im Video,
    // ohne dass jemand klicken muss. Außerhalb der Demo bleibt es interaktiv.
    if (demo.running) {
      const recCard = $(".agent-card.rec", b);
      const rec = answer.agents.find((a) => {
        const cat = a.id ? catalogById(a.id) : null;
        const live = cat ? isActive(cat.id) : !!a.active;
        return (a.recommended || (cat && cat.recommended)) && !live;
      });
      if (recCard && rec) scheduleAutoBook(recCard, rec);
    }
  }

  // Spielt die Einrichtungs-Animation ab und ersetzt den Button durch eine grüne
  // Aktiv-Bestätigung — reuse der Erfolgs-Bildsprache aus dem Aktions-Block.
  async function bookAgent(item, agent) {
    if (item.dataset.booked === "1") return;
    item.dataset.booked = "1";
    const foot = $(".ag-foot", item);
    const btn = $(".ag-book", foot);
    if (btn) btn.replaceWith(el("span", "ag-pending", `<span class="spinner"></span>Agent wird eingerichtet…`));
    await sleep(reducedMotion() ? 0 : 900);
    item.classList.add("on", "just-booked");
    const pend = $(".ag-pending", foot);
    const done = el("span", "ag-live",
      `✓ Aktiviert · ab sofort Teil Ihres Teams · erste Auswertung heute Abend`);
    if (pend) pend.replaceWith(done); else foot.appendChild(done);
    if (agent && agent.id) await rentAgent(agent.id);
    refreshNavCounts();
    if (!demo.running) showFleetToast(agent);
    scrollBottom();
  }

  // Token-gesicherter Auto-Buchungs-Beat für die Geführte Demo.
  async function scheduleAutoBook(item, agent) {
    const token = demo.token;
    await sleep(reducedMotion() ? 200 : 1250);
    if (!demo.running || token !== demo.token) return;
    await bookAgent(item, agent);
  }

  // ---------- Matching ----------
  function matchScenario(text) {
    const q = text.toLowerCase();
    // Exakter/Fast-Treffer auf die Musterfrage bevorzugen
    let best = null, bestScore = 0;
    SCENARIOS.forEach((s) => {
      let score = 0;
      if (q.includes(s.question.toLowerCase().slice(0, 12))) score += 5;
      s.keywords.forEach((k) => { if (q.includes(k)) score += k.split(" ").length; });
      if (score > bestScore) { bestScore = score; best = s; }
    });
    return bestScore >= 1 ? best : null;
  }

  function fallbackAnswer(text) {
    // Graceful: sucht die drei relevantesten Dokumente per Stichwort.
    // Gesperrte Dokumente werden NIE als lesbare Quelle zurückgegeben
    // (permission-faithful): sie erscheinen nur über das `withheld`-Signal.
    const q = text.toLowerCase();
    const scored = Object.values(DOCS).filter((d) => !d.locked).map((d) => {
      const hay = (d.title + " " + d.snippet + " " + d.type).toLowerCase();
      let s = 0;
      q.split(/\s+/).forEach((w) => { if (w.length > 3 && hay.includes(w)) s += 1; });
      return { d, s };
    }).filter((x) => x.s > 0).sort((a, b) => b.s - a.s).slice(0, 3);

    // Gesperrte Treffer separat ermitteln → als „nicht freigegeben" ausweisen,
    // ohne Inhalt/Zitat preiszugeben (permission-faithful auch bei freien Fragen).
    const lockedHits = Object.values(DOCS).filter((d) => d.locked).filter((d) => {
      const hay = (d.title + " " + d.snippet + " " + d.type + " " + (d.lockedRole || "")).toLowerCase();
      return q.split(/\s+/).some((w) => w.length > 3 && hay.includes(w));
    });
    const withheld = lockedHits.length ? {
      count: lockedHits.length,
      role: lockedHits[0].lockedRole,
      note: "AI Studio respektiert die bestehenden Berechtigungen Ihres Kontos. Diese Dokumente werden Ihnen nicht angezeigt und flossen nicht in die Antwort ein.",
      docs: lockedHits.map((d) => d.id),
    } : null;

    if (scored.length === 0) {
      return {
        text: withheld
          ? "Zu Ihrer Frage sind ausschließlich Dokumente vorhanden, die <b>für Sie nicht freigegeben</b> sind — siehe unten. AI Studio zeigt deren Inhalt nicht an."
          : "Ich konnte zu dieser Frage keine passenden Dokumente in der Demo-Wissensbasis finden. Probieren Sie eine der vorgeschlagenen Beispielfragen — die Demo-Firma umfasst Finanzen, HR, Verträge, Audit und Berichte.",
        reasoning: withheld
          ? ["Frage entgegengenommen.", "Zugriffsrechte des Kontos geprüft.", `${withheld.count} Treffer als „${withheld.role}" klassifiziert — Inhalt nicht gelesen und nicht angezeigt (fail-closed).`]
          : ["Frage entgegengenommen.", "Wissensbasis durchsucht — kein ausreichend relevanter Treffer.", "Ehrliche Rückmeldung statt Halluzination (fail-closed)."],
        sources: [],
        confidence: 30,
        withheld,
        related: [],
        followups: SCENARIOS.slice(0, 3).map((s) => s.question),
      };
    }
    return {
      text: `Ich habe <b>${scored.length} relevante Dokument(e)</b> zu Ihrer Frage gefunden. Öffnen Sie eine Quelle für die Details:`,
      reasoning: ["Frage per Stichwortsuche über alle Module ausgewertet.", "Nach Relevanz sortiert.", "Nur Dokumente angezeigt, für die eine Leseberechtigung besteht."],
      sources: scored.map((x, i) => ({ docId: x.d.id, relevance: 88 - i * 9, quote: x.d.snippet })),
      confidence: 72,
      withheld,
      related: scored.map((x) => x.d.id),
      followups: SCENARIOS.slice(0, 2).map((s) => s.question),
    };
  }

  // ---------- Bibliotheks-Ansicht (Module außer Wissen) ----------
  function renderLibraryView(key) {
    const scroll = $("#scroll");
    scroll.innerHTML = "";
    $("#composer").style.display = "none";
    const wrap = el("div", "wrap");
    const mod = MODULES.find((m) => m.key === key);

    const head = el("div", "lib-head");
    head.innerHTML = `<h2>${mod.label}</h2><p>${mod.hint}</p>`;
    wrap.appendChild(head);

    // Vorgeschlagene Fragen für dieses Modul
    const sugg = MODULE_SUGGESTIONS[key] || [];
    if (sugg.length) {
      const box = el("div", "chips");
      box.style.marginBottom = "20px";
      sugg.forEach((sid) => {
        const s = SCENARIOS.find((x) => x.id === sid);
        if (!s) return;
        const chip = el("button", "chip", "✦ " + s.question);
        chip.onclick = () => ask(s.question);
        box.appendChild(chip);
      });
      wrap.appendChild(box);
    }

    // Dokumente dieses Moduls
    const grid = el("div", "doc-grid");
    Object.values(DOCS).filter((d) => d.module === key).forEach((d) => {
      const card = el("div", d.locked ? "doc-card locked" : "doc-card");
      if (d.locked) {
        card.innerHTML =
          `<div class="top"><span class="ficon lock">🔒</span><div><div class="t">${d.title}</div><div class="type">${escapeHtml(d.type)}</div></div></div>` +
          `<div class="snip">${d.snippet}</div>` +
          `<div class="foot"><span class="no-access">🔒 Kein Zugriff — ${escapeHtml(d.lockedRole)}</span><span>${d.date}</span></div>`;
      } else {
        card.innerHTML =
          `<div class="top"><span class="ficon">${d.type === "E-Mail" ? "✉" : "▤"}</span><div><div class="t">${d.title}</div><div class="type">${d.type}</div></div></div>` +
          `<div class="snip">${d.snippet}</div>` +
          `<div class="foot"><span>${d.author}</span><span>${d.date}</span></div>`;
      }
      card.onclick = () => openViewer(d.id);
      grid.appendChild(card);
    });
    if (!grid.children.length) grid.appendChild(el("p", null, "<span style='color:var(--ink-faint)'>Keine Dokumente in diesem Modul.</span>"));
    wrap.appendChild(grid);
    scroll.appendChild(wrap);
  }

  // ---------- Einstellungen (Datenquellen) ----------
  function renderSettingsView() {
    const scroll = $("#scroll");
    scroll.innerHTML = "";
    $("#composer").style.display = "none";
    const wrap = el("div", "wrap");
    wrap.appendChild(el("div", "lib-head", `<h2>Datenquellen</h2><p>Angebundene Systeme der ${COMPANY.name}. In der Demo simuliert.</p>`));

    const srcs = [
      { i: "📁", t: "SharePoint", s: "Richtlinien, Verträge, Vorstandsprotokolle" },
      { i: "🗄", t: "Fileserver", s: "Controlling, Projekte, Nachweise" },
      { i: "🧾", t: "SAP S/4HANA", s: "Rechnungen, Bestellungen, Wareneingänge" },
      { i: "✉", t: "Exchange / E-Mail", s: "Postfächer & Anhänge" },
      { i: "📊", t: "Excel & Berichte", s: "Quartalszahlen, ESG-Kennzahlen" },
      { i: "🔒", t: "Berechtigungen", s: "Zugriff je Nutzer wird respektiert" },
    ];
    const grid = el("div", "sources-grid");
    srcs.forEach((x) => {
      const tile = el("div", "src-tile");
      tile.innerHTML = `<span class="si">${x.i}</span><div><div class="t">${x.t}</div><div class="s">${x.s}</div></div><span class="on">● verbunden</span>`;
      grid.appendChild(tile);
    });
    wrap.appendChild(grid);

    const note = el("p", null,
      `<span style="font-size:12.5px;color:var(--ink-faint)">Hinweis: Alle Inhalte dieser Demo sind frei erfunden. Es werden keine echten Kundendaten verarbeitet.</span>`);
    note.style.marginTop = "18px";
    wrap.appendChild(note);

    if (isLive()) {
      const up = el("div", "upload-box");
      up.innerHTML = `<h3>Dokument in die Wissensbasis legen</h3>` +
        `<p>Textdatei bis 2 MB. Der Inhalt ist nur für diesen Mandanten suchbar und erscheint in den Antworten.</p>`;
      const input = el("input");
      input.type = "file";
      input.accept = ".txt,.md,.csv,.json";
      const status = el("p");
      input.onchange = async () => {
        if (!input.files || !input.files[0]) return;
        status.textContent = "Wird aufgenommen…";
        try {
          const out = await AISTUDIO.upload(input.files[0]);
          status.textContent = "Aufgenommen: " + (out.id || input.files[0].name);
        } catch (e) {
          status.textContent = e.message || "Upload fehlgeschlagen.";
        }
      };
      up.append(input, status);
      wrap.appendChild(up);
    }

    scroll.appendChild(wrap);
  }

  // ---------- Dokumentenviewer ----------
  function openViewer(docId, highlightQuote) {
    const doc = DOCS[docId];
    if (!doc) return;
    $("#vTitle").textContent = doc.title;
    $("#vType").textContent = doc.type;
    $("#vMeta").innerHTML = doc.locked
      ? metaRow("Pfad", doc.path) +
        metaRow("Eigentümer", doc.author) +
        metaRow("Klassifizierung", doc.classification || "Vertraulich") +
        metaRow("Freigegeben für", doc.lockedRole) +
        metaRow("Typ", doc.type)
      : metaRow("Pfad", doc.path) +
        metaRow("Autor", doc.author) +
        metaRow("Erstellt", doc.date) +
        (doc.updated ? metaRow("Status", doc.updated) : "") +
        metaRow("Typ", doc.type);

    const body = $("#vBody");
    body.innerHTML = "";
    // Entscheidungskette: gehört dieses Dokument zum Beleg-Pfad, bekommt der
    // Viewer oben einen kompakten „Schritt n von 3"-Navigator (Vor/Zurück).
    const chainIdx = chainStepIndex(docId);
    if (chainIdx >= 0) body.appendChild(buildChainNav(chainIdx));
    body.appendChild(doc.locked ? buildLockedPaper(doc) : buildPaper(doc, highlightQuote));
    body.scrollTop = 0;

    $("#overlay").classList.add("open");
    $("#viewer").classList.add("open");
  }

  // Position eines Dokuments innerhalb der Entscheidungskette (–1 = nicht Teil).
  function chainStepIndex(docId) {
    if (typeof DECISION_CHAIN === "undefined" || !DECISION_CHAIN.steps) return -1;
    return DECISION_CHAIN.steps.findIndex((s) => s.docId === docId);
  }

  // Kompakter Ketten-Navigator im Viewer: macht die drei Belege der
  // Entscheidungskette (Lieferant → Einkauf/CFO → Vorstand) direkt beim Lesen
  // navigierbar — „Schritt n von 3" mit Vor/Zurück und anklickbaren Punkten.
  // Datengetrieben aus DECISION_CHAIN, dieselbe Quelle wie der Chat-Block.
  function buildChainNav(idx) {
    const steps = DECISION_CHAIN.steps;
    const nav = el("div", "vchain");

    const head = el("div", "vc-head");
    head.innerHTML =
      `<span class="vc-title">⛓ Entscheidungskette</span>` +
      `<span class="vc-count">Schritt <b>${idx + 1}</b> von ${steps.length}</span>`;
    nav.appendChild(head);

    const track = el("div", "vc-track");
    steps.forEach((step, i) => {
      const cls = "vc-step" + (i === idx ? " current" : "") + (i < idx ? " done" : "");
      const node = el("button", cls,
        `<span class="vc-dot"></span>` +
        `<span class="vc-lab"><span class="vc-date">${escapeHtml(step.date)}</span>` +
        `<span class="vc-actor">${escapeHtml(step.actor)}</span></span>`);
      node.onclick = () => { if (i !== idx) openViewer(step.docId); };
      if (i === idx) node.setAttribute("aria-current", "step");
      track.appendChild(node);
    });
    nav.appendChild(track);

    const foot = el("div", "vc-foot");
    const prev = el("button", "vc-nav" + (idx === 0 ? " disabled" : ""), "← Voriger Beleg");
    const next = el("button", "vc-nav" + (idx === steps.length - 1 ? " disabled" : ""), "Nächster Beleg →");
    if (idx > 0) prev.onclick = () => openViewer(steps[idx - 1].docId);
    if (idx < steps.length - 1) next.onclick = () => openViewer(steps[idx + 1].docId);
    foot.appendChild(prev);
    foot.appendChild(el("span", "vc-here", escapeHtml(steps[idx].label)));
    foot.appendChild(next);
    nav.appendChild(foot);

    return nav;
  }

  // Gesperrtes Dokument: zeigt bewusst KEINEN Inhalt, sondern eine
  // „Zugriff verweigert"-Ansicht — die Kernidee „Sie sehen nur, was Sie dürfen".
  function buildLockedPaper(doc) {
    const paper = el("div", "paper paper-locked");
    paper.appendChild(el("div", "lock-badge", "🔒"));
    paper.appendChild(el("div", "lock-title", "Zugriff verweigert"));
    paper.appendChild(el("div", "lock-sub",
      `Dieses Dokument ist als <b>${escapeHtml(doc.classification || "vertraulich")}</b> eingestuft und nur für <b>${escapeHtml(doc.lockedRole)}</b> freigegeben.`));
    paper.appendChild(el("p", "lock-note",
      "AI Studio zeigt und verarbeitet ausschließlich Dokumente, für die Ihr Konto berechtigt ist. Der Inhalt bleibt vollständig verborgen — auch in Antworten und Zusammenfassungen."));
    return paper;
  }

  // Baut die „Papier"-Darstellung eines Dokuments (Briefkopf, Beleg-Text,
  // Stempel/Unterschrift je nach Typ). Highlights liegen jetzt IM Dokument.
  function buildPaper(doc, highlightQuote) {
    const skin = DOC_SKINS[doc.type] || defaultSkin;
    const paper = el("div", `paper paper-${skin.cat}`);

    // E-Mail-Skin: Von/An/Betreff-Kopf statt Briefkopf; der Betreff ersetzt
    // die generische Dokument-Überschrift.
    if (skin.cat === "email") {
      paper.appendChild(buildMailHead(doc));
    } else {
      paper.appendChild(buildLetterhead(doc, skin));
      paper.appendChild(el("div", "dtitle", escapeHtml(doc.title)));
    }

    doc.body.forEach((p, i) => {
      if (i === 0) return; // erste Zeile ist die Dokument-Überschrift → als Titel oben
      const hl = p.highlight || (highlightQuote && p.t.includes(highlightQuote.slice(0, 24)));
      const para = el("p", hl ? "dp hl" : "dp", markupClause(escapeHtml(p.t)));
      paper.appendChild(para);
    });

    if (skin.cat === "email" && doc.quoted) paper.appendChild(buildQuoted(doc.quoted));

    if (skin.cat === "beleg" && doc.lineItems) paper.appendChild(buildLineItems(doc.lineItems));

    if (skin.stamp) paper.appendChild(buildStamp(skin.stamp, doc));
    if (skin.sign) paper.appendChild(buildSignature(doc));
    return paper;
  }

  // Positionszeilen-Tabelle für Belege (Rechnung/Bestellung/Wareneingang).
  // Rein datengetrieben aus doc.lineItems; Netto/USt/Brutto-Fußzeilen optional.
  function buildLineItems(li) {
    const box = el("div", "litems");
    const rows = (li.rows || []).map((r) =>
      `<tr><td class="pos">${escapeHtml(r.pos)}</td>` +
      `<td class="desc">${escapeHtml(r.desc)}</td>` +
      `<td class="num">${escapeHtml(r.qty || "—")}</td>` +
      `<td class="num">${escapeHtml(r.unit || "—")}</td>` +
      `<td class="num sum">${escapeHtml(r.sum || "—")}</td></tr>`
    ).join("");

    const foot = [];
    if (li.net) foot.push(footRow("Netto", li.net, false));
    if (li.vat) foot.push(footRow("USt" + (li.vatRate ? " " + escapeHtml(li.vatRate) : ""), li.vat, false));
    if (li.gross) foot.push(footRow(li.grossLabel || "Rechnungsbetrag brutto", li.gross, true));

    box.innerHTML =
      (li.ref ? `<div class="li-ref">${escapeHtml(li.ref)}</div>` : "") +
      `<table class="li-table"><thead><tr>` +
      `<th class="pos">Pos.</th><th class="desc">Bezeichnung</th>` +
      `<th class="num">Menge</th><th class="num">Einzelpreis</th><th class="num">Summe</th>` +
      `</tr></thead><tbody>${rows}</tbody>` +
      (foot.length ? `<tfoot>${foot.join("")}</tfoot>` : "") +
      `</table>`;
    return box;
  }
  function footRow(label, value, strong) {
    const cls = strong ? "li-foot total" : "li-foot";
    return `<tr class="${cls}"><td colspan="4">${label}</td><td class="num">${escapeHtml(value)}</td></tr>`;
  }

  function buildLetterhead(doc, skin) {
    const iss = skin.extIssuer
      ? { name: doc.author.replace(/\s*\(.*\)$/, ""), sub: "Lieferant" }
      : { name: COMPANY.name, sub: COMPANY.tagline };
    const initials = iss.name.replace(/[^A-Za-zÄÖÜ]/g, "").slice(0, 2).toUpperCase() || "AI";
    const lh = el("div", "lh");
    lh.innerHTML =
      `<div class="org"><span class="mark">${initials}</span>` +
      `<span><span class="on">${escapeHtml(iss.name)}</span>` +
      `<span class="os">${escapeHtml(iss.sub)}</span></span></div>` +
      `<div class="ref"><span class="rt">${escapeHtml(doc.type)}</span>` +
      `<span class="rl">${escapeHtml(doc.title)}</span>` +
      `<span class="rl">Datum: ${escapeHtml(doc.date)}</span></div>`;
    return lh;
  }

  // E-Mail-Kopf: Von/An/(CC)/Betreff/Gesendet + optionaler Anhang-Chip.
  // Macht die Kern-Erzählung „Wissen steckt in E-Mails" im Viewer sichtbar.
  function buildMailHead(doc) {
    const name = doc.author.replace(/\s*\(.*\)$/, "");
    const initials = name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase() || "@";
    const rows =
      mailRow("Von", doc.from || doc.author) +
      mailRow("An", doc.to || "") +
      (doc.cc ? mailRow("Cc", doc.cc) : "") +
      mailRow("Betreff", doc.subject || doc.title, "sub") +
      mailRow("Gesendet", doc.sent || doc.date);
    const att = doc.attachment
      ? `<div class="mail-att"><span class="clip">📎</span>` +
        `<span class="an">${escapeHtml(doc.attachment.name)}</span>` +
        (doc.attachment.size ? `<span class="as">${escapeHtml(doc.attachment.size)}</span>` : "") +
        `</div>`
      : "";
    const head = el("div", "mail");
    head.innerHTML =
      `<div class="mail-top"><span class="mmark">${initials}</span>` +
      `<div class="mail-rows">${rows}</div></div>` + att;
    return head;
  }

  // Zitierter Verlauf unter einer E-Mail (die vorherige Nachricht).
  function buildQuoted(q) {
    const box = el("div", "mail-quote");
    box.appendChild(el("div", "mq-head",
      `Am ${escapeHtml(q.date)} schrieb ${escapeHtml(q.from)}:`));
    (q.lines || []).forEach((l) => box.appendChild(el("p", "mq-line", escapeHtml(l))));
    return box;
  }

  function buildStamp(stamp, doc) {
    const s = el("div", `stamp stamp-${stamp.tone}`);
    s.innerHTML = `<span class="st">${escapeHtml(stamp.text)}</span><span class="sd">${escapeHtml(doc.date)}</span>`;
    return s;
  }

  function buildSignature(doc) {
    const box = el("div", "sig");
    const place = el("div", "sig-place", `München, ${escapeHtml(doc.date)}`);
    const row = el("div", "sig-row");
    row.innerHTML =
      `<div class="col"><div class="line">Meridian Industrie GmbH</div></div>` +
      `<div class="col"><div class="line">${escapeHtml(doc.author.replace(/\s*\(.*\)$/, ""))}</div></div>`;
    box.appendChild(place);
    box.appendChild(row);
    return box;
  }

  // Hebt führende Klausel-/Gliederungsmarken (§3, Teil B §5, TOP 1) fett hervor.
  function markupClause(escaped) {
    return escaped.replace(/^(§\s?\d+[a-z]?|Teil [A-C] §\s?\d+|TOP \d+)(:|\b)/,
      '<b class="cl">$1</b>$2');
  }
  function metaRow(k, v) { return `<div class="row"><span>${k}</span><span>${escapeHtml(v)}</span></div>`; }
  function mailRow(k, v, cls) { return `<div class="mr${cls ? " " + cls : ""}"><span class="mk">${k}</span><span class="mv">${escapeHtml(v)}</span></div>`; }
  function closeViewer() { $("#overlay").classList.remove("open"); $("#viewer").classList.remove("open"); }
  function wireViewer() {
    $("#vClose").onclick = closeViewer;
    $("#overlay").onclick = closeViewer;
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeViewer(); });
  }

  // ---------- Globale Suche (Command-Palette) ----------
  // Ein sichtbarer „Was steckt alles drin?"-Moment: durchsucht den GESAMTEN
  // Wissensspeicher (alle Module) live nach Titel/Typ/Snippet/Autor. Leeres Feld
  // zeigt das komplette Inventar — macht die schiere Menge greifbar.
  const search = { open: false, results: [], sel: 0 };

  function moduleLabel(key) {
    const m = MODULES.find((x) => x.key === key);
    return m ? m.label : key;
  }

  function wireSearch() {
    const co = $("#searchCompany");
    if (co) co.textContent = COMPANY.name;

    $("#searchTrigger").onclick = openSearch;
    $("#searchClose").onclick = closeSearch;
    $("#searchOverlay").addEventListener("click", (e) => { if (e.target.id === "searchOverlay") closeSearch(); });

    const input = $("#searchInput");
    input.addEventListener("input", () => renderSearchResults(input.value));
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { e.preventDefault(); moveSel(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); moveSel(-1); }
      else if (e.key === "Enter") { e.preventDefault(); openSelected(); }
    });

    // Strg/⌘ + K öffnet/schließt die Suche von überall.
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        search.open ? closeSearch() : openSearch();
      } else if (e.key === "Escape" && search.open) {
        closeSearch();
      }
    });
  }

  function openSearch() {
    if (demo.running) return; // während der Geführten Demo nicht stören
    search.open = true;
    $("#searchOverlay").hidden = false;
    const input = $("#searchInput");
    input.value = "";
    renderSearchResults("");
    input.focus();
  }

  function closeSearch() {
    if (!search.open) return;
    search.open = false;
    $("#searchOverlay").hidden = true;
  }

  // Filtert alle Dokumente über einen Haystack aus Titel/Typ/Snippet/Autor/Modul.
  function matchDocs(q) {
    const all = Object.values(DOCS);
    const query = q.trim().toLowerCase();
    if (!query) return all;
    return all.filter((d) => {
      const hay = [d.title, d.type, d.snippet, d.author, moduleLabel(d.module)]
        .filter(Boolean).join(" ").toLowerCase();
      return hay.includes(query);
    });
  }

  function renderSearchResults(q) {
    const box = $("#searchResults");
    const results = matchDocs(q);
    search.results = results;
    search.sel = 0;
    const total = Object.keys(DOCS).length;

    const meta = $("#searchCount");
    const query = q.trim();
    meta.innerHTML = query
      ? `<b>${results.length}</b> von ${total} Dokumenten für „${escapeHtml(query)}"`
      : `<b>${total}</b> Dokumente im Wissensspeicher — tippen zum Filtern`;

    box.innerHTML = "";
    if (!results.length) {
      box.appendChild(el("div", "sp-empty", `Kein Dokument passt zu „${escapeHtml(query)}".`));
      return;
    }
    results.forEach((d, i) => {
      const row = el("div", d.locked ? "sp-row locked" : "sp-row");
      if (i === 0) row.classList.add("sel");
      const icon = d.locked ? "🔒" : (d.type === "E-Mail" ? "✉" : "▤");
      const side = d.locked
        ? `<span class="sp-lock">🔒 Kein Zugriff</span><span class="sp-type">${escapeHtml(d.type)}</span>`
        : `<span class="sp-tag">${escapeHtml(moduleLabel(d.module))}</span><span class="sp-type">${escapeHtml(d.type)}</span>`;
      row.innerHTML =
        `<span class="ficon">${icon}</span>` +
        `<div class="sp-main"><div class="sp-t">${hlMatch(d.title, query)}</div>` +
        `<div class="sp-s">${hlMatch(d.snippet || "", query)}</div></div>` +
        `<div class="sp-side">${side}</div>`;
      row.onclick = () => { closeSearch(); openViewer(d.id); };
      row.addEventListener("mouseenter", () => setSel(i));
      box.appendChild(row);
    });
  }

  function setSel(i) {
    const rows = $("#searchResults").children;
    if (!rows.length) return;
    search.sel = Math.max(0, Math.min(i, rows.length - 1));
    for (let k = 0; k < rows.length; k++) rows[k].classList.toggle("sel", k === search.sel);
  }

  function moveSel(delta) {
    const rows = $("#searchResults").children;
    if (!rows.length || rows[0].classList.contains("sp-empty")) return;
    setSel(search.sel + delta);
    rows[search.sel].scrollIntoView({ block: "nearest" });
  }

  function openSelected() {
    const d = search.results[search.sel];
    if (!d) return;
    closeSearch();
    openViewer(d.id);
  }

  // Escaped den Text und hebt Treffer des Suchbegriffs mit <mark> hervor (sicher).
  function hlMatch(text, q) {
    if (!q) return escapeHtml(text);
    const lower = text.toLowerCase(), ql = q.toLowerCase();
    let out = "", i = 0, idx;
    while ((idx = lower.indexOf(ql, i)) !== -1) {
      out += escapeHtml(text.slice(i, idx));
      out += "<mark>" + escapeHtml(text.slice(idx, idx + ql.length)) + "</mark>";
      i = idx + ql.length;
    }
    return out + escapeHtml(text.slice(i));
  }

  // ---------- Composer ----------
  function wireComposer() {
    const ta = $("#input");
    const send = $("#send");
    const submit = () => { if (demo.running) return; const v = ta.value; ta.value = ""; ta.style.height = "auto"; ask(v); };
    send.onclick = submit;
    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
    });
    ta.addEventListener("input", () => { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 120) + "px"; });
  }

  // ---------- Zahlen-Count-up (Video-Politur) ----------
  // Reduzierte Bewegung respektieren: dann Endwerte sofort, ohne Animation.
  function reducedMotion() {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
    catch (e) { return false; }
  }

  // Zerlegt einen deutschen Zahlwert wie „18,4 %", „87.584 €", „-12,0 %", „80 t".
  // Gibt null zurück, wenn es KEIN reiner Zahlwert ist (Jahre, Datum, PO-Nummern,
  // Text) → diese bleiben unangetastet. Sicher: verlangt Dezimalkomma ODER Einheit,
  // damit blanke Ganzzahlen/Jahre (2026) und Datumsangaben nicht animiert werden.
  const NUM_UNIT = "(%|€|t|Mio\\.\\s*€|Mrd\\.\\s*€|GWh|kWh|Punkte)";
  const NUM_RE = new RegExp(
    "^([+\\u2212-]?)((?:\\d{1,3}(?:\\.\\d{3})+|\\d+)(?:,(\\d+))?)(?:\\s*" + NUM_UNIT + ")?$"
  );
  function parseGermanNumber(raw) {
    const m = NUM_RE.exec(raw.trim());
    if (!m) return null;
    const decimals = m[3] ? m[3].length : 0;
    const unit = m[4] || "";
    if (decimals === 0 && !unit) return null; // blanke Ganzzahl (z. B. Jahr) → nicht animieren
    const sign = m[1] === "+" ? "+" : (m[1] ? "-" : "");
    const value = Number(m[2].replace(/\./g, "").replace(",", "."));
    if (!isFinite(value)) return null;
    return { sign, value, decimals, unit };
  }

  function fmtGerman(value, decimals) {
    const fixed = value.toFixed(decimals);
    const parts = fixed.split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return parts.length > 1 ? parts[0] + "," + parts[1] : parts[0];
  }

  // Zählt einen Zahl-Knoten von 0 auf den Zielwert (easeOut), ~700 ms.
  function countUp(node, value, decimals, unit) {
    if (!node) return;
    const u = unit || "";
    const finalText = fmtGerman(value, decimals) + u;
    if (reducedMotion() || value <= 0) { node.textContent = finalText; return; }
    node.classList.add("counting");
    const dur = 720, t0 = performance.now();
    function frame(now) {
      const p = Math.min(1, (now - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      node.textContent = fmtGerman(value * eased, decimals) + u;
      if (p < 1) { requestAnimationFrame(frame); }
      else { node.textContent = finalText; node.classList.remove("counting"); }
    }
    requestAnimationFrame(frame);
  }

  // Findet alle fett gesetzten Kernzahlen im Antworttext und zählt sie dezent hoch.
  function animateCounts(scope) {
    if (reducedMotion()) return; // Endwerte stehen bereits im DOM
    scope.querySelectorAll("b").forEach((b) => {
      if (b.children.length) return; // nur reine Textknoten
      const p = parseGermanNumber(b.textContent);
      if (!p) return;
      const unit = p.unit ? " " + p.unit : "";
      const prefix = p.sign; // „-"/„+" bleibt stehen, Betrag zählt hoch
      b.classList.add("counting");
      const dur = 760, t0 = performance.now(), final = prefix + fmtGerman(p.value, p.decimals) + unit;
      (function step(now) {
        const pr = Math.min(1, (now - t0) / dur);
        const eased = 1 - Math.pow(1 - pr, 3);
        b.textContent = prefix + fmtGerman(p.value * eased, p.decimals) + unit;
        if (pr < 1) requestAnimationFrame(step);
        else { b.textContent = final; b.classList.remove("counting"); }
      })(performance.now());
    });
  }

  // Lässt einen Meter-Balken (ein <i> mit inline gesetzter Breite) von 0 auf
  // seinen im DOM stehenden Zielwert hochlaufen — passend zum Zahlen-Count-up
  // (countUp/animateCounts). Rein visuell; liest die Zielbreite aus `style.width`,
  // setzt sie auf 0 und animiert per requestAnimationFrame (easeOutCubic, ~760 ms).
  // prefers-reduced-motion → sofort auf den Endwert (kein Sprung-Artefakt).
  function animateBar(fill, dur) {
    if (!fill) return;
    const final = fill.style.width || "0%";
    const target = parseFloat(final) || 0;
    if (reducedMotion() || target <= 0) { fill.style.width = final; return; }
    const d = dur || 760, t0 = performance.now();
    fill.style.width = "0%";
    (function step(now) {
      const pr = Math.min(1, (now - t0) / d);
      const eased = 1 - Math.pow(1 - pr, 3);
      fill.style.width = (target * eased).toFixed(2) + "%";
      if (pr < 1) requestAnimationFrame(step);
      else fill.style.width = final;
    })(performance.now());
  }

  // Relevanz-Balken in der Konfidenz-Herleitung (Popover) laufen beim ERSTEN
  // Öffnen des Popovers einmalig hoch — analog zum Konfidenz-Balken im Kopf.
  function wireConfPopBars(card) {
    const conf = $(".conf.has-pop", card);
    if (!conf) return;
    let done = false;
    const run = () => {
      if (done) return; done = true;
      conf.querySelectorAll(".cp-bar i").forEach((f) => animateBar(f, 640));
    };
    conf.addEventListener("mouseenter", run);
    conf.addEventListener("focus", run, true);
  }

  function isTeamJump(text) {
    const q = (text || "").toLowerCase();
    if (/dazubuchen|dazu buchen|weiteren agenten/.test(q)) return false;
    return /mietplattform|digitales team|mein team|modul team|agenten mieten|marktplatz|abrechnung der agenten/.test(q);
  }

  // ---------- Modul Team: Mietplattform ----------
  function renderTeamView() {
    const scroll = $("#scroll");
    scroll.innerHTML = "";
    $("#composer").style.display = "none";
    const wrap = el("div", "wrap wide");
    wrap.appendChild(el("div", "lib-head",
      `<h2>Digitale Mitarbeiter mieten</h2>` +
      `<p>Wie eine Neueinstellung — monatlich kündbar, ab 400 €, sofort im selben Firmenwissen zu Hause.</p>`));

    const tabs = el("div", "team-tabs");
    [
      { id: "fleet", label: "Ihr Team" },
      { id: "market", label: "Marktplatz" },
      { id: "billing", label: "Abrechnung" },
      { id: "work", label: "Aufträge" },
    ].forEach((t) => {
      const b = el("button", "team-tab" + (teamUi.tab === t.id ? " on" : ""), t.label);
      b.onclick = () => { teamUi.tab = t.id; if (t.id !== "market") teamUi.detailId = null; renderTeamView(); };
      tabs.appendChild(b);
    });
    wrap.appendChild(tabs);

    if (teamUi.tab === "fleet") wrap.appendChild(renderFleetPane());
    else if (teamUi.tab === "market") wrap.appendChild(teamUi.detailId ? renderDetailPane(teamUi.detailId) : renderMarketPane());
    else if (teamUi.tab === "billing") wrap.appendChild(renderBillingPane());
    else wrap.appendChild(renderWorkPane());

    scroll.appendChild(wrap);
    refreshNavCounts();
  }

  function renderFleetPane() {
    const box = el("div");
    const active = activeAgents();
    const paid = paidCount();
    const kpis = el("div", "kpi-row");
    [
      { k: "Aktive Agenten", v: String(active.length), s: paid ? (paid + " gemietet") : "Auskunft inklusive" },
      { k: "Monatliche Miete", v: formatEur(monthlyTotal()), s: "netto · monatlich kündbar" },
      { k: "Nächste Rechnung", v: nextInvoiceGerman(), s: "SEPA-Lastschrift" },
      { k: "vs. 1 FTE Controlling", v: "400 €", s: "statt ~6.500 € Personalkosten" },
    ].forEach((x) => {
      kpis.appendChild(el("div", "kpi", `<div class="k">${x.k}</div><div class="v">${x.v}</div><div class="s">${x.s}</div>`));
    });
    box.appendChild(kpis);

    const roster = el("div", "roster");
    const catalog = typeof AGENT_CATALOG !== "undefined" ? AGENT_CATALOG : [];
    const shown = catalog.filter((a) => isRented(a.id));
    shown.forEach((a) => roster.appendChild(rosterCard(a)));
    box.appendChild(roster);

    const cta = el("div", "team-cta");
    cta.innerHTML = `<p><b>Team erweitern.</b> Reporting, Rechnungen, Verträge und vier weitere Spezialisten stehen bereit.</p>`;
    const go = el("button", "btn primary", "Marktplatz öffnen →");
    go.onclick = () => { teamUi.tab = "market"; teamUi.detailId = null; renderTeamView(); };
    cta.appendChild(go);
    box.appendChild(cta);
    return box;
  }

  function rosterCard(a) {
    const l = leaseOf(a.id) || { status: "active", since: a.included ? "inklusive" : "—" };
    const paused = l.status === "paused";
    const card = el("div", "roster-card" + (paused ? " paused" : ""));
    const badge = paused
      ? `<span class="ag-badge">Pausiert</span>`
      : `<span class="ag-badge active">● Aktiv</span>`;
    const left = el("div");
    left.innerHTML =
      `<div class="rc-top">` +
      `<span class="ag-ic">${a.icon}</span>` +
      `<span class="ag-h"><span class="ag-name">${escapeHtml(a.name)}</span>` +
      `<span class="ag-role">${escapeHtml(a.role)}</span></span>${badge}</div>` +
      `<div class="ag-desc" style="margin:8px 0 10px">${escapeHtml(a.desc)}</div>` +
      `<div class="rc-meta">` +
      `<span>Miete <b>${escapeHtml(agentPriceLabel(a))}${a.included ? "" : " / Monat"}</b></span>` +
      `<span>Seit <b>${escapeHtml(l.since)}</b></span>` +
      `<span>Nächster Lauf <b>${escapeHtml(a.nextRun || "—")}</b></span>` +
      `</div>`;
    const actions = el("div", "rc-actions");
    if (!a.included) {
      const work = el("button", "btn primary", "Auftrag geben");
      work.onclick = () => { teamUi.tab = "work"; teamUi.workId = a.id; teamUi.workOut = null; renderTeamView(); };
      const pause = el("button", "btn ghost", paused ? "Fortsetzen" : "Pausieren");
      pause.onclick = async () => { await togglePause(a.id); renderTeamView(); };
      const cancel = el("button", "btn warn", "Kündigen");
      cancel.onclick = async () => {
        if (cancel.dataset.arm === "1") { await cancelAgent(a.id); renderTeamView(); return; }
        cancel.dataset.arm = "1";
        cancel.textContent = "Wirklich kündigen?";
        setTimeout(() => {
          if (cancel.dataset.arm === "1") { cancel.dataset.arm = ""; cancel.textContent = "Kündigen"; }
        }, 4000);
      };
      actions.append(work, pause, cancel);
    } else {
      const go = el("button", "btn", "Im Chat fragen");
      go.onclick = () => selectModule("wissen");
      actions.appendChild(go);
    }
    card.append(left, actions);
    return card;
  }

  function renderMarketPane() {
    const box = el("div");
    const filters = el("div", "mkt-filters");
    const cats = typeof AGENT_CATEGORIES !== "undefined" ? AGENT_CATEGORIES : [{ id: "alle", label: "Alle" }];
    cats.forEach((c) => {
      const b = el("button", "chip-f" + (teamUi.filter === c.id ? " on" : ""), c.label);
      b.onclick = () => { teamUi.filter = c.id; renderTeamView(); };
      filters.appendChild(b);
    });
    box.appendChild(filters);

    const grid = el("div", "mkt-grid");
    const list = (typeof AGENT_CATALOG !== "undefined" ? AGENT_CATALOG : [])
      .filter((a) => teamUi.filter === "alle" || a.category === teamUi.filter);
    list.forEach((a) => {
      const live = isActive(a.id);
      const rec = a.recommended && !live;
      const card = el("button", "mkt-card" + (rec ? " rec" : "") + (live ? " on" : ""));
      const skills = (a.skills || []).slice(0, 3).map((s) => `<span class="sk-chip">${escapeHtml(s)}</span>`).join("");
      const badge = live
        ? `<span class="ag-badge active">● Im Team</span>`
        : (rec ? `<span class="ag-badge rec">Empfohlen</span>` : `<span class="ag-badge" style="background:var(--bg);color:var(--ink-soft)">${escapeHtml(catLabel(a.category))}</span>`);
      card.innerHTML =
        `<div class="ag-top"><span class="ag-ic">${a.icon}</span>` +
        `<span class="ag-h"><span class="ag-name">${escapeHtml(a.name)}</span>` +
        `<span class="ag-role">${escapeHtml(a.role)}</span></span>${badge}</div>` +
        `<div class="ag-desc">${escapeHtml(a.desc)}</div>` +
        `<div class="mkt-skills">${skills}</div>` +
        `<div class="mkt-sla">${escapeHtml(a.sla || "")}</div>` +
        `<div class="mkt-foot"><span class="ag-price">${escapeHtml(agentPriceLabel(a))}` +
        (a.included ? "" : `<span class="ag-per"> / Monat</span>`) + `</span></div>`;
      card.onclick = () => { teamUi.detailId = a.id; renderTeamView(); };
      grid.appendChild(card);
    });
    box.appendChild(grid);
    return box;
  }

  function catLabel(id) {
    const c = (typeof AGENT_CATEGORIES !== "undefined" ? AGENT_CATEGORIES : []).find((x) => x.id === id);
    return c ? c.label : id;
  }

  function renderDetailPane(id) {
    const a = catalogById(id);
    const box = el("div");
    if (!a) return el("p", null, "Agent nicht gefunden.");
    const back = el("button", "btn ghost detail-back", "← Marktplatz");
    back.onclick = () => { teamUi.detailId = null; renderTeamView(); };
    box.appendChild(back);

    const grid = el("div", "detail-grid");
    const main = el("div", "detail-main");
    main.innerHTML =
      `<div class="ag-top" style="margin-bottom:12px"><span class="ag-ic">${a.icon}</span>` +
      `<span class="ag-h"><span class="ag-name" style="font-size:20px">${escapeHtml(a.name)}</span>` +
      `<span class="ag-role">${escapeHtml(a.role)}</span></span></div>` +
      `<p>${escapeHtml(a.long || a.desc)}</p>` +
      `<h3>Kann ausliefern</h3><ul class="skill-list">${(a.skills || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>` +
      `<h3 style="margin-top:16px">Werkzeuge</h3><ul class="skill-list">${(a.tools || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>`;
    if (a.sampleWork) {
      const sm = el("div", "sample-box");
      sm.innerHTML = `<div class="when">${escapeHtml(a.sampleWork.when || "")} · ${escapeHtml(a.sampleWork.kicker || "")}</div>` +
        `<b>${escapeHtml(a.sampleWork.title || "")}</b>${a.sampleWork.html || ""}`;
      main.appendChild(sm);
    }

    const side = el("div", "detail-side");
    side.innerHTML =
      `<div class="side-price">${escapeHtml(agentPriceLabel(a))}${a.included ? "" : "<span class='ag-per'> / Monat</span>"}</div>` +
      `<div class="side-row"><span>SLA</span><span>${escapeHtml(a.sla || "—")}</span></div>` +
      `<div class="side-row"><span>Einsatz</span><span>${escapeHtml(a.hours || "—")}</span></div>` +
      `<div class="side-row"><span>Verantwortlich</span><span>${escapeHtml(a.owner || "—")}</span></div>` +
      `<div class="side-row"><span>Erste Lieferung</span><span>${escapeHtml(a.firstDeliverable || "—")}</span></div>` +
      `<div class="side-row"><span>Kündigung</span><span>monatlich, ohne Frist</span></div>`;
    const act = el("div");
    act.style.marginTop = "16px";
    if (isActive(id)) {
      act.appendChild(el("div", "ag-live", "✓ Bereits Teil Ihres Teams"));
      const work = el("button", "btn primary");
      work.style.marginTop = "10px";
      work.style.width = "100%";
      work.textContent = a.included ? "Im Chat fragen" : "Auftrag geben";
      work.onclick = () => {
        if (a.included) selectModule("wissen");
        else { teamUi.tab = "work"; teamUi.workId = id; teamUi.workOut = null; renderTeamView(); }
      };
      act.appendChild(work);
    } else if (leaseOf(id) && leaseOf(id).status === "paused") {
      const resume = el("button", "btn primary", "Miete fortsetzen");
      resume.style.width = "100%";
      resume.onclick = async () => { await togglePause(id); renderTeamView(); };
      act.appendChild(resume);
    } else {
      const rent = el("button", "btn primary", "Jetzt mieten · " + agentPriceLabel(a) + " / Monat");
      rent.style.width = "100%";
      rent.onclick = () => openRent(id);
      act.appendChild(rent);
    }
    side.appendChild(act);
    grid.append(main, side);
    box.appendChild(grid);
    return box;
  }

  function renderBillingPane() {
    const box = el("div");
    const catalog = typeof AGENT_CATALOG !== "undefined" ? AGENT_CATALOG : [];
    const rows = catalog.filter((a) => isRented(a.id));
    const table = el("table", "bill-table");
    let body = `<tr><th>Agent</th><th>Status</th><th class="num">Preis / Monat</th></tr>`;
    rows.forEach((a) => {
      const l = leaseOf(a.id) || { status: "active" };
      const billed = l.status === "active" && !a.included;
      const status = a.included ? "Inklusive" : (l.status === "paused" ? "Pausiert — nicht berechnet" : "Aktiv");
      const price = billed ? formatEur(a.price) : (a.included ? "0 €" : "0 €");
      body += `<tr><td><b>${escapeHtml(a.name)}</b><div style="font-size:12px;color:var(--ink-faint)">${escapeHtml(a.role)}</div></td>` +
        `<td>${status}</td><td class="num">${price}</td></tr>`;
    });
    body += `<tr><td class="sum" colspan="2">Summe netto</td><td class="num sum">${formatEur(monthlyTotal())}</td></tr>`;
    table.innerHTML = body;
    box.appendChild(table);

    const pay = el("div", "pay-row");
    pay.appendChild(el("div", "pay-tile",
      `<div class="k">Nächste Lastschrift</div><div class="v">${nextInvoiceGerman()} · ${formatEur(monthlyTotal())}</div>` +
      `<div class="k" style="margin-top:8px">Mandat SEPA (Demo)</div><div class="v">DE12 1001 0000 0123 4567 89 · Meridian Industrie GmbH</div>`));
    pay.appendChild(el("div", "pay-tile",
      `<div class="k">Preis-Pfad</div><div class="v">Audit 149 € → Wissensbasis ab 5.000 € → Agent ab 400 €/Monat</div>` +
      `<div class="k" style="margin-top:8px">Ersparnis-Hinweis</div><div class="v">Ein Reporting-Agent ersetzt keine Abteilung — er liefert die Vorlage, die ein Controller sonst 2 Tage schreibt.</div>`));
    box.appendChild(pay);
    box.appendChild(el("p", "bill-note",
      "Demo-Abrechnung: keine echte Lastschrift. Monatlich kündbar, keine Mindestlaufzeit. Pausierte Agenten erscheinen in der nächsten Periode nicht auf der Rechnung."));
    return box;
  }

  function renderWorkPane() {
    const box = el("div");
    const specialists = (typeof AGENT_CATALOG !== "undefined" ? AGENT_CATALOG : []).filter((a) => isActive(a.id));
    if (!specialists.length) {
      box.appendChild(el("p", "work-empty", "Noch kein Agent aktiv. Mieten Sie einen Spezialisten im Marktplatz."));
      return box;
    }
    if (!teamUi.workId || !specialists.some((a) => a.id === teamUi.workId)) {
      teamUi.workId = (specialists.find((a) => !a.included) || specialists[0]).id;
    }
    const pick = el("div", "work-pick");
    specialists.forEach((a) => {
      const b = el("button", "work-agent" + (teamUi.workId === a.id ? " on" : ""),
        `<span>${a.icon}</span>${escapeHtml(a.name)}`);
      b.onclick = () => { teamUi.workId = a.id; teamUi.workOut = null; renderTeamView(); };
      pick.appendChild(b);
    });
    box.appendChild(pick);

    const agent = catalogById(teamUi.workId);
    const tasks = (agent && agent.tasks) || [];
    const chips = el("div", "chips");
    chips.style.marginBottom = "16px";
    tasks.forEach((t) => {
      const b = el("button", "chip", "▶ " + t.label);
      b.onclick = () => runAgentTask(agent, t);
      chips.appendChild(b);
    });
    box.appendChild(chips);

    const out = el("div", "work-out");
    out.id = "workOut";
    if (teamUi.workOut) {
      out.innerHTML = teamUi.workOut;
    } else {
      out.appendChild(el("p", "work-empty",
        agent && agent.included
          ? "Der Auskunfts-Agent arbeitet im Modul Wissen. Stellen Sie dort eine Frage — oder mieten Sie einen Spezialisten für wiederkehrende Lieferungen."
          : "Wählen Sie einen Auftrag. Der Agent liefert aus Ihrem Firmenwissen, mit derselben Beleg-Disziplin wie der Chat."));
    }
    box.appendChild(out);
    return box;
  }

  async function runAgentTask(agent, task) {
    if (task.jump === "wissen") { selectModule("wissen"); return; }
    const host = $("#workOut");
    if (!host) return;
    host.innerHTML = `<div class="thinking"><span class="spinner"></span><span class="steps">${escapeHtml(agent.name)} arbeitet…</span></div>`;
    if (isLive()) {
      try {
        const result = await AISTUDIO.runAgent(agent.id, task.label || task.hint || "Auftrag");
        const html =
          `<div class="wo-kicker">${escapeHtml(agent.name)} · Live-Auftrag</div>` +
          `<h3>${escapeHtml(task.label || "Lieferung")}</h3>` +
          `<div class="text">${result.text || ""}</div>`;
        teamUi.workOut = html;
        host.innerHTML = html;
      } catch (e) {
        host.innerHTML = `<p class="work-empty">${escapeHtml(e.message || "Auftrag fehlgeschlagen.")}</p>`;
      }
      return;
    }
    await sleep(reducedMotion() ? 0 : 720);
    const o = task.output || {};
    const html =
      `<div class="wo-kicker">${escapeHtml(agent.name)} · ${escapeHtml(o.kicker || "Lieferung")}</div>` +
      `<h3>${escapeHtml(o.title || task.label)}</h3>` +
      (o.html || "<p>Keine Lieferung hinterlegt.</p>");
    teamUi.workOut = html;
    host.innerHTML = html;
    const actions = el("div", "block actions");
    actions.style.borderTop = "1px solid var(--line)";
    actions.style.marginTop = "12px";
    actions.appendChild(el("div", "block-title", "↗ Ergebnis weiterreichen"));
    const row = el("div", "act-row");
    const send = el("button", "act primary", "✉ An Vorstand senden");
    send.onclick = () => runAction(row, "send", briefingNumber({ text: o.title || task.label, confidence: 90 }));
    row.appendChild(send);
    actions.appendChild(row);
    host.appendChild(actions);
  }

  function wireRentOverlay() {
    const ov = $("#rentOverlay");
    if (!ov) return;
    const closeBtn = $("#rentClose");
    if (closeBtn) closeBtn.onclick = closeRent;
    ov.addEventListener("click", (e) => { if (e.target === ov) closeRent(); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && ov && !ov.hidden) closeRent();
    });
  }

  function closeRent() {
    const ov = $("#rentOverlay");
    if (ov) ov.hidden = true;
  }

  function openRent(id) {
    const a = catalogById(id);
    const ov = $("#rentOverlay");
    if (!a || !ov) return;
    $("#rentTitle").textContent = a.name + " mieten";
    $("#rentBody").innerHTML =
      `<div class="rp-agent"><span class="ag-ic">${a.icon}</span>` +
      `<span class="ag-h"><span class="ag-name">${escapeHtml(a.name)}</span>` +
      `<span class="ag-role">${escapeHtml(a.role)}</span></span></div>` +
      `<p>Sie mieten <b>${escapeHtml(a.name)}</b> für <b>${escapeHtml(agentPriceLabel(a))} / Monat</b>, kündbar zum Monatsende, ohne Mindestlaufzeit.</p>` +
      `<ul class="rp-list">` +
      `<li>Start: <b>heute</b> — ${escapeHtml(a.firstDeliverable || "erste Lieferung folgt.")}</li>` +
      `<li>Arbeitet mit demselben Firmenwissen wie der Auskunfts-Agent.</li>` +
      `<li>Nächste Lastschrift: <b>${nextInvoiceGerman()}</b> (Demo, keine echte Zahlung).</li>` +
      `</ul>`;
    const foot = $("#rentFoot");
    foot.innerHTML = "";
    const cancel = el("button", "btn", "Abbrechen");
    cancel.onclick = closeRent;
    const ok = el("button", "btn primary", "Bestätigen · " + agentPriceLabel(a) + " / Monat");
    ok.onclick = async () => {
      ok.disabled = true;
      ok.textContent = "Wird eingerichtet…";
      await sleep(reducedMotion() ? 0 : 900);
      await rentAgent(id);
      closeRent();
      showFleetToast(a);
      teamUi.tab = "fleet";
      teamUi.detailId = null;
      if (currentModule === "team") renderTeamView();
      else refreshNavCounts();
    };
    foot.append(cancel, ok);
    ov.hidden = false;
  }

  let toastTimer = 0;
  function hideFleetToast() {
    const t = $("#fleetToast");
    if (t) t.hidden = true;
    if (toastTimer) clearTimeout(toastTimer);
  }

  function showFleetToast(agent) {
    const t = $("#fleetToast");
    if (!t || !agent) return;
    t.innerHTML = "";
    t.appendChild(el("span", null, "✓ " + agent.name + " ist Teil Ihres Teams"));
    const go = el("button", null, "Im Team ansehen");
    go.onclick = () => { hideFleetToast(); teamUi.tab = "fleet"; selectModule("team"); };
    t.appendChild(go);
    t.hidden = false;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(hideFleetToast, 5200);
  }

  // ---------- Helfer ----------
  function scrollBottom() { const s = $("#scroll"); s.scrollTop = s.scrollHeight; }
  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  document.addEventListener("DOMContentLoaded", init);
})();
