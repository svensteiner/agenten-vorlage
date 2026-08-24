/*
 * Live-Produkt-Client. Additiv: ohne /api/health (file://, statischer Demo-Server)
 * bleibt die bestehende Demo unverändert. Bei laufendem product-Server: Login,
 * echte FTS-Antworten, persistente Flotte, Agent-Jobs.
 */
(function (global) {
  "use strict";

  const TOKEN_KEY = "aistudio.token";
  const params = new URLSearchParams(location.search || "");
  const forceDemo = params.get("demo") === "1";

  const api = {
    live: false,
    token: null,
    user: null,
    org: null,
    fleet: null,

    isLive: function () { return !!(this.live && this.token); },

    _headers: function (extra) {
      const h = Object.assign({ "Accept": "application/json" }, extra || {});
      if (this.token) h.Authorization = "Bearer " + this.token;
      return h;
    },

    request: async function (path, opts) {
      opts = opts || {};
      const headers = this._headers(opts.json ? { "Content-Type": "application/json" } : opts.headers);
      const res = await fetch(path, {
        method: opts.method || "GET",
        headers: headers,
        body: opts.json ? JSON.stringify(opts.json) : opts.body,
      });
      let data = null;
      const ct = res.headers.get("content-type") || "";
      if (ct.indexOf("application/json") >= 0) {
        data = await res.json();
      } else {
        data = { detail: await res.text() };
      }
      if (!res.ok) {
        const err = new Error((data && (data.detail || data.message)) || ("HTTP " + res.status));
        err.status = res.status;
        err.body = data;
        throw err;
      }
      return data;
    },

    boot: async function () {
      if (forceDemo) return;
      if (location.protocol === "file:") return;
      try {
        const health = await fetch("/api/health", { headers: { "Accept": "application/json" } });
        if (!health.ok) return;
        const body = await health.json();
        if (!body || !body.ok) return;
        this.live = true;
        this.health = body;
      } catch (e) {
        return;
      }
      try { this.token = sessionStorage.getItem(TOKEN_KEY); } catch (e) { this.token = null; }
      if (this.token) {
        try {
          await this.hydrate();
          return;
        } catch (e) {
          this.token = null;
          try { sessionStorage.removeItem(TOKEN_KEY); } catch (err) { /* ignore */ }
        }
      }
      await this.loginUi();
      await this.hydrate();
    },

    loginUi: function () {
      const self = this;
      return new Promise((resolve) => {
        const ov = document.getElementById("loginOverlay");
        if (!ov) { resolve(); return; }
        ov.hidden = false;
        const form = document.getElementById("loginForm");
        const err = document.getElementById("loginError");
        const email = document.getElementById("loginEmail");
        const password = document.getElementById("loginPassword");
        const demoHint = document.getElementById("loginDemoEmail");
        if (demoHint && self.health && self.health.demo_email) {
          demoHint.textContent = self.health.demo_email;
        }
        if (email && self.health && self.health.demo_email) email.value = self.health.demo_email;
        if (password) password.value = "Meridian2026!";
        const onSubmit = async (e) => {
          e.preventDefault();
          if (err) { err.hidden = true; err.textContent = ""; }
          const btn = form.querySelector("button[type=submit]");
          if (btn) { btn.disabled = true; btn.textContent = "Anmelden…"; }
          try {
            const out = await self.request("/api/auth/login", {
              method: "POST",
              json: { email: email.value.trim(), password: password.value },
            });
            self.token = out.token;
            self.user = out.user;
            try { sessionStorage.setItem(TOKEN_KEY, out.token); } catch (err2) { /* ignore */ }
            ov.hidden = true;
            form.removeEventListener("submit", onSubmit);
            resolve();
          } catch (ex) {
            if (err) {
              err.hidden = false;
              err.textContent = ex.message || "Anmeldung fehlgeschlagen.";
            }
          } finally {
            if (btn) { btn.disabled = false; btn.textContent = "Anmelden"; }
          }
        };
        form.addEventListener("submit", onSubmit);
      });
    },

    hydrate: async function () {
      const me = await this.request("/api/me");
      this.user = me.user;
      this.org = me.org;
      const docs = await this.request("/api/docs");
      this.applyDocs(docs.docs || []);
      this.fleet = await this.request("/api/fleet");
    },

    applyDocs: function (list) {
      if (typeof DOCS !== "object" || !DOCS) return;
      Object.keys(DOCS).forEach((k) => { delete DOCS[k]; });
      (list || []).forEach((d) => { if (d && d.id) DOCS[d.id] = d; });
    },

    refreshFleet: async function () {
      this.fleet = await this.request("/api/fleet");
      return this.fleet;
    },

    ask: function (q) {
      return this.request("/api/ask", { method: "POST", json: { q: q } });
    },

    fleetAction: async function (agentId, action) {
      const out = await this.request("/api/fleet", {
        method: "POST",
        json: { agent_id: agentId || "", action: action },
      });
      this.fleet = { leases: out.leases || {} };
      return this.fleet;
    },

    runAgent: function (agentId, task) {
      return this.request("/api/agents/run", {
        method: "POST",
        json: { agent_id: agentId, task: task },
      });
    },

    upload: async function (file) {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch("/api/docs/upload", {
        method: "POST",
        headers: this._headers(),
        body: body,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload fehlgeschlagen");
      const docs = await this.request("/api/docs");
      this.applyDocs(docs.docs || []);
      return data;
    },

    logout: function () {
      this.token = null;
      this.user = null;
      try { sessionStorage.removeItem(TOKEN_KEY); } catch (e) { /* ignore */ }
      location.reload();
    },
  };

  global.AISTUDIO = api;
})(window);
