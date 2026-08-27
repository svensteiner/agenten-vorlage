/*
 * Live-Produkt-Client. Additiv: ohne /api/health (file://, statischer Demo-Server)
 * bleibt die bestehende Demo unverändert. Bei laufendem product-Server: Login,
 * echte FTS-Antworten, persistente Flotte, Agent-Jobs, Mandantenbetrieb.
 */
(function (global) {
  "use strict";

  const TOKEN_KEY = "aistudio.token";
  const params = new URLSearchParams(location.search || "");
  const forceDemo = params.get("demo") === "1";

  function detailMessage(data, fallback) {
    if (!data) return fallback || "Fehler";
    const d = data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d.map(function (x) { return (x && (x.msg || x.message)) || String(x); }).join(" ");
    }
    return data.message || fallback || "Fehler";
  }

  const api = {
    live: false,
    token: null,
    user: null,
    org: null,
    fleet: null,
    health: null,
    storage: null,

    isLive: function () { return !!(this.live && this.token); },
    isDemoTenant: function () {
      if (this.tenantDemo) return true;
      return !!(this.health && this.health.demo && this.user && this.user.email &&
        /@meridian\.example$/.test(this.user.email));
    },
    canMutateFleet: function () {
      if (!this.isLive()) return true;
      const r = this.user && this.user.role;
      return r === "admin" || r === "cfo";
    },
    isAdmin: function () { return !!(this.user && this.user.role === "admin"); },

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
        const err = new Error(detailMessage(data, "HTTP " + res.status));
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

    _showTab: function (tab) {
      const loginForm = document.getElementById("loginForm");
      const registerForm = document.getElementById("registerForm");
      const title = document.getElementById("loginTitle");
      const lead = document.getElementById("loginLead");
      document.querySelectorAll(".login-tab").forEach(function (b) {
        b.classList.toggle("on", b.getAttribute("data-tab") === tab);
      });
      if (tab === "register") {
        if (loginForm) loginForm.hidden = true;
        if (registerForm) registerForm.hidden = false;
        if (title) title.textContent = "Mandant anlegen";
        if (lead) lead.textContent = "Eigene Instanz: leere Wissensbasis, Auskunfts-Agent inklusive, Sie sind Admin.";
      } else {
        if (loginForm) loginForm.hidden = false;
        if (registerForm) registerForm.hidden = true;
        if (title) title.textContent = "Anmelden";
        if (lead) lead.textContent = "Ihre private Wissensbasis und gemieteten Agenten — auf Ihrer Infrastruktur.";
      }
    },

    loginUi: function () {
      const self = this;
      return new Promise((resolve) => {
        const ov = document.getElementById("loginOverlay");
        if (!ov) { resolve(); return; }
        ov.hidden = false;
        const form = document.getElementById("loginForm");
        const registerForm = document.getElementById("registerForm");
        const err = document.getElementById("loginError");
        const email = document.getElementById("loginEmail");
        const password = document.getElementById("loginPassword");
        const hint = document.getElementById("loginHint");
        const demoHint = document.getElementById("loginDemoEmail");
        const registerTab = document.getElementById("registerTab");
        const demo = !!(self.health && self.health.demo);
        if (!self.health || !self.health.allow_register) {
          if (registerTab) registerTab.hidden = true;
        }
        if (hint) hint.hidden = !demo;
        if (demo) {
          if (demoHint && self.health.demo_email) demoHint.textContent = self.health.demo_email;
          if (email && self.health.demo_email) email.value = self.health.demo_email;
          if (password) password.value = "Meridian2026!";
        } else if (password) {
          password.value = "";
        }
        document.querySelectorAll(".login-tab").forEach(function (b) {
          b.onclick = function () { self._showTab(b.getAttribute("data-tab")); };
        });
        self._showTab("login");

        const finish = function (out) {
          self.token = out.token;
          self.user = out.user;
          self.org = out.org || self.org;
          try { sessionStorage.setItem(TOKEN_KEY, out.token); } catch (err2) { /* ignore */ }
          ov.hidden = true;
          resolve();
        };

        const onSubmit = async function (e) {
          e.preventDefault();
          if (err) { err.hidden = true; err.textContent = ""; }
          const btn = form.querySelector("button[type=submit]");
          if (btn) { btn.disabled = true; btn.textContent = "Anmelden…"; }
          try {
            const out = await self.request("/api/auth/login", {
              method: "POST",
              json: { email: email.value.trim(), password: password.value },
            });
            form.removeEventListener("submit", onSubmit);
            finish(out);
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

        if (registerForm) {
          const rerr = document.getElementById("registerError");
          registerForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            if (rerr) { rerr.hidden = true; rerr.textContent = ""; }
            const btn = registerForm.querySelector("button[type=submit]");
            if (btn) { btn.disabled = true; btn.textContent = "Wird angelegt…"; }
            try {
              const out = await self.request("/api/auth/register", {
                method: "POST",
                json: {
                  org_name: document.getElementById("regOrg").value.trim(),
                  name: document.getElementById("regName").value.trim(),
                  email: document.getElementById("regEmail").value.trim(),
                  password: document.getElementById("regPassword").value,
                },
              });
              finish(out);
            } catch (ex) {
              if (rerr) {
                rerr.hidden = false;
                rerr.textContent = ex.message || "Registrierung fehlgeschlagen.";
              }
            } finally {
              if (btn) { btn.disabled = false; btn.textContent = "Mandant erstellen"; }
            }
          });
        }
      });
    },

    hydrate: async function () {
      const me = await this.request("/api/me");
      this.user = me.user;
      this.org = me.org;
      this.tenantDemo = !!me.demo;
      this.storage = me.storage || null;
      this.health = Object.assign({}, this.health || {}, {
        demo: !!me.demo,
        llm: me.llm || (this.health && this.health.llm) || {},
        backup_age_hours: me.backup_age_hours,
        backup_ok: me.backup_ok,
      });
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
      if (!res.ok) throw new Error(detailMessage(data, "Upload fehlgeschlagen"));
      const docs = await this.request("/api/docs");
      this.applyDocs(docs.docs || []);
      return data;
    },

    deleteDoc: async function (id) {
      await this.request("/api/docs/" + encodeURIComponent(id), { method: "DELETE" });
      const docs = await this.request("/api/docs");
      this.applyDocs(docs.docs || []);
    },

    logout: async function () {
      try { await this.request("/api/auth/logout", { method: "POST", json: {} }); } catch (e) { /* ignore */ }
      this.token = null;
      this.user = null;
      try { sessionStorage.removeItem(TOKEN_KEY); } catch (e) { /* ignore */ }
      location.reload();
    },
  };

  global.AISTUDIO = api;
})(window);
