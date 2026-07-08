/*
 * AI Studio Demo — Interaktionslogik.
 * Reines Vanilla-JS, keine Abhängigkeiten, läuft per Doppelklick (file://).
 * Rendert Chat, gestreamte Antworten, Quellen und den Dokumentenviewer.
 * Datenquelle: data.js (COMPANY, MODULES, DOCS, SCENARIOS, MODULE_SUGGESTIONS).
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

  // „Geführte Demo": spielt alle Szenarien hands-free nacheinander ab.
  // token: monoton steigend; ein Stopp erhöht ihn und lässt laufende Schleifen aussteigen.
  const demo = { running: false, token: 0 };

  // Dokument-Skins: geben jedem Dokumenttyp im Viewer eine realistische
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
    "E-Mail":               { cat: "email" },
  };
  const defaultSkin = { cat: "bericht" };

  // ---------- Bootstrapping ----------
  function init() {
    renderSidebar();
    renderCompanyCard();
    selectModule("wissen");
    wireComposer();
    wireViewer();
    wireDemo();
    wireSearch();
    wireOnboarding();
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

    const list = SCENARIOS; // die 7 Szenarien in kuratierter Reihenfolge
    for (let i = 0; i < list.length; i++) {
      if (token !== demo.token) return;
      prog.textContent = `${i + 1} / ${list.length}`;
      await typeIntoComposer(list[i].question, token);
      if (token !== demo.token) return;
      await ask(list[i].question);
      if (token !== demo.token) return;
      await sleep(i === list.length - 1 ? 1600 : 2800); // Lesepause
    }
    if (token === demo.token) resetDemoUi();
  }

  function stopDemo() {
    demo.token++; // laufende Schleife steigt beim nächsten Check aus
    resetDemoUi();
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
    nav.appendChild(el("div", "nav-label", "Module"));
    MODULES.forEach((m) => {
      const btn = el("button", "nav-item", `<span class="ic">${m.icon}</span><span>${m.label}</span>`);
      btn.dataset.key = m.key;
      btn.onclick = () => selectModule(m.key);
      nav.appendChild(btn);
    });
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

  // ---------- Antwort streamen ----------
  async function streamAnswer(wrap, answer) {
    const msg = el("div", "msg");
    const card = el("div", "answer");
    const confCls = answer.confidence >= 90 ? "" : "mid";
    // Kopf: „Beantwortet in X,X s"-Signal (Tempo) links vom Konfidenz-Meter.
    const secs = answerSeconds(answer);
    card.appendChild(el("div", "head",
      `<span class="ai">✦</span><span class="who">AI Studio</span>` +
      `<span class="speed" title="Antwortzeit">⚡ Beantwortet in <b class="sp-val">0,0 s</b></span>` +
      `<span class="conf"><span class="conf-meter">Konfidenz` +
      `<span class="conf-bar ${confCls}"><i style="width:${answer.confidence}%"></i></span>` +
      `<b>${answer.confidence}%</b></span></span>`));
    const textEl = el("div", "text");
    textEl.classList.add("cursor");
    card.appendChild(textEl);
    msg.appendChild(card);
    wrap.appendChild(msg);
    scrollBottom();

    // Tempo-Signal sofort hochzählen — lässt das System „live" und schnell wirken.
    countUp($(".sp-val", card), secs, 1, " s");

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
    revealBlocks(card);
    scrollBottom();
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
    if (li.gross) foot.push(footRow("Rechnungsbetrag brutto", li.gross, true));

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

  // ---------- Helfer ----------
  function scrollBottom() { const s = $("#scroll"); s.scrollTop = s.scrollHeight; }
  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  document.addEventListener("DOMContentLoaded", init);
})();
