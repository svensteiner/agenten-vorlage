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
    card.appendChild(el("div", "head",
      `<span class="ai">✦</span><span class="who">AI Studio</span>` +
      `<span class="conf"><span class="conf-meter">Konfidenz` +
      `<span class="conf-bar ${confCls}"><i style="width:${answer.confidence}%"></i></span>` +
      `<b>${answer.confidence}%</b></span></span>`));
    const textEl = el("div", "text");
    textEl.classList.add("cursor");
    card.appendChild(textEl);
    msg.appendChild(card);
    wrap.appendChild(msg);
    scrollBottom();

    // Text zeichenweise „tippen" (HTML-sicher: wir tippen den fertigen HTML-String schrittweise)
    await typeHtml(textEl, answer.text);
    textEl.classList.remove("cursor");

    // Danach die strukturierten Blöcke einblenden
    appendReasoning(card, answer.reasoning);
    appendSources(card, answer.sources);
    appendRelated(card, answer.related);
    appendFollowups(card, answer.followups);
    scrollBottom();
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
    const q = text.toLowerCase();
    const scored = Object.values(DOCS).map((d) => {
      const hay = (d.title + " " + d.snippet + " " + d.type).toLowerCase();
      let s = 0;
      q.split(/\s+/).forEach((w) => { if (w.length > 3 && hay.includes(w)) s += 1; });
      return { d, s };
    }).filter((x) => x.s > 0).sort((a, b) => b.s - a.s).slice(0, 3);

    if (scored.length === 0) {
      return {
        text: "Ich konnte zu dieser Frage keine passenden Dokumente in der Demo-Wissensbasis finden. Probieren Sie eine der vorgeschlagenen Beispielfragen — die Demo-Firma umfasst Finanzen, HR, Verträge, Audit und Berichte.",
        reasoning: ["Frage entgegengenommen.", "Wissensbasis durchsucht — kein ausreichend relevanter Treffer.", "Ehrliche Rückmeldung statt Halluzination (fail-closed)."],
        sources: [],
        confidence: 30,
        related: [],
        followups: SCENARIOS.slice(0, 3).map((s) => s.question),
      };
    }
    return {
      text: `Ich habe <b>${scored.length} relevante Dokument(e)</b> zu Ihrer Frage gefunden. Öffnen Sie eine Quelle für die Details:`,
      reasoning: ["Frage per Stichwortsuche über alle Module ausgewertet.", "Nach Relevanz sortiert.", "Nur Dokumente angezeigt, für die eine Leseberechtigung besteht."],
      sources: scored.map((x, i) => ({ docId: x.d.id, relevance: 88 - i * 9, quote: x.d.snippet })),
      confidence: 72,
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
      const card = el("div", "doc-card");
      card.innerHTML =
        `<div class="top"><span class="ficon">▤</span><div><div class="t">${d.title}</div><div class="type">${d.type}</div></div></div>` +
        `<div class="snip">${d.snippet}</div>` +
        `<div class="foot"><span>${d.author}</span><span>${d.date}</span></div>`;
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
    $("#vMeta").innerHTML =
      metaRow("Pfad", doc.path) +
      metaRow("Autor", doc.author) +
      metaRow("Erstellt", doc.date) +
      (doc.updated ? metaRow("Status", doc.updated) : "") +
      metaRow("Typ", doc.type);

    const body = $("#vBody");
    body.innerHTML = "";
    body.appendChild(buildPaper(doc, highlightQuote));
    body.scrollTop = 0;

    $("#overlay").classList.add("open");
    $("#viewer").classList.add("open");
  }

  // Baut die „Papier"-Darstellung eines Dokuments (Briefkopf, Beleg-Text,
  // Stempel/Unterschrift je nach Typ). Highlights liegen jetzt IM Dokument.
  function buildPaper(doc, highlightQuote) {
    const skin = DOC_SKINS[doc.type] || defaultSkin;
    const paper = el("div", `paper paper-${skin.cat}`);

    paper.appendChild(buildLetterhead(doc, skin));

    const title = el("div", "dtitle", escapeHtml(doc.title));
    paper.appendChild(title);

    doc.body.forEach((p, i) => {
      if (i === 0) return; // erste Zeile ist die Dokument-Überschrift → als Titel oben
      const hl = p.highlight || (highlightQuote && p.t.includes(highlightQuote.slice(0, 24)));
      const para = el("p", hl ? "dp hl" : "dp", markupClause(escapeHtml(p.t)));
      paper.appendChild(para);
    });

    if (skin.stamp) paper.appendChild(buildStamp(skin.stamp, doc));
    if (skin.sign) paper.appendChild(buildSignature(doc));
    return paper;
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
  function closeViewer() { $("#overlay").classList.remove("open"); $("#viewer").classList.remove("open"); }
  function wireViewer() {
    $("#vClose").onclick = closeViewer;
    $("#overlay").onclick = closeViewer;
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeViewer(); });
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

  // ---------- Helfer ----------
  function scrollBottom() { const s = $("#scroll"); s.scrollTop = s.scrollHeight; }
  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  document.addEventListener("DOMContentLoaded", init);
})();
