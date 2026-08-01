"use strict";

const form = document.querySelector("#order-form");
const orderButton = document.querySelector("#order-button");
const formMessage = document.querySelector("#form-message");
const customerArea = document.querySelector("#customer-area");
const verifyButton = document.querySelector("#verify-button");
const reportButton = document.querySelector("#report-button");
const agentState = document.querySelector("#agent-state");
const verificationMessage = document.querySelector("#verification-message");
const verificationDetail = document.querySelector("#verification-detail");
const verificationCard = document.querySelector("#verification-card");
const reportCard = document.querySelector("#report-card");
const companyInput = document.querySelector("#company-name");
const syntheticCheckbox = document.querySelector("#synthetic-only");
const STORAGE_KEY = "aistudioxyz-kmu-demo-order-v1";

let csrfToken = "";
let stored = loadStoredJourney();
let orderId = stored.orderId || "";
let verifyKey = stored.verifyKey || operationKey("verify");
let checkoutKey = stored.checkoutKey || operationKey("checkout");

function operationKey(prefix) {
  const random = globalThis.crypto.randomUUID();
  return `${prefix}-${random}`;
}

function loadStoredJourney() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

function persistJourney(companyName) {
  stored = {
    checkoutKey,
    verifyKey,
    orderId,
    companyName: companyName || stored.companyName || ""
  };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch {
    // The journey remains usable for the current page if storage is disabled.
  }
}

function showReady(order, scroll = false) {
  orderId = order.order_id;
  companyInput.value = order.display_name || stored.companyName || "";
  syntheticCheckbox.checked = true;
  companyInput.disabled = true;
  syntheticCheckbox.disabled = true;
  orderButton.disabled = true;
  formMessage.textContent = "Bestellung erfolgreich · Gesamtkosten 0 €";
  customerArea.hidden = false;
  persistJourney(companyInput.value);
  if (scroll) {
    customerArea.scrollIntoView({behavior: "smooth", block: "start"});
  }
}

function showAccepted() {
  agentState.className = "state accepted";
  agentState.textContent = "Abgenommen";
  verificationDetail.textContent = "3/3 identische Kontrollläufe";
  verificationCard.classList.add("done");
  reportCard.classList.add("done");
  reportCard.querySelector(".tick").textContent = "✓";
  verificationMessage.textContent = "Bericht bereit · 3/3 geprüft";
  verifyButton.disabled = true;
  reportButton.disabled = false;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.method === "POST") {
    headers.set("Content-Type", "application/json");
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(path, {...options, headers});
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Der lokale Vorgang ist fehlgeschlagen.");
  }
  return payload;
}

async function prepareSession() {
  const session = await api("/api/session");
  csrfToken = session.csrf_token;
  persistJourney(stored.companyName || "");
  if (stored.companyName) {
    companyInput.value = stored.companyName;
  }
  if (!orderId) {
    return;
  }
  try {
    const order = await api(`/api/demo-orders/${orderId}`);
    showReady(order);
    if (order.status === "accepted" && order.acceptance.passed) {
      showAccepted();
    }
  } catch {
    orderId = "";
    persistJourney(stored.companyName || "");
    orderButton.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!csrfToken) {
    formMessage.textContent = "Lokale Sitzung ist noch nicht bereit.";
    return;
  }
  orderButton.disabled = true;
  formMessage.textContent = "Agent und Musterdaten werden vorbereitet …";
  persistJourney(companyInput.value);
  try {
    const order = await api("/api/demo-orders", {
      method: "POST",
      body: JSON.stringify({
        company_name: companyInput.value,
        idempotency_key: checkoutKey,
        synthetic_only: syntheticCheckbox.checked,
        confirmed_zero_cost: true
      })
    });
    showReady(order, true);
  } catch (error) {
    formMessage.textContent = error.message;
    orderButton.disabled = false;
  }
});

verifyButton.addEventListener("click", async () => {
  verifyButton.disabled = true;
  agentState.className = "state working";
  agentState.textContent = "Prüfung läuft";
  verificationDetail.textContent = "Kennzahlen werden 3× reproduziert …";
  verificationMessage.textContent = "Datenabstimmung und drei identische Kontrollläufe laufen.";
  try {
    const order = await api(`/api/demo-orders/${orderId}/verify`, {
      method: "POST",
      body: JSON.stringify({idempotency_key: verifyKey})
    });
    if (!order.acceptance.passed || order.acceptance.repeatable_run_count !== 3) {
      throw new Error("Die 3/3-Prüfung wurde nicht bestätigt.");
    }
    showAccepted();
  } catch (error) {
    agentState.className = "state error";
    agentState.textContent = "Prüfung offen";
    verificationMessage.textContent = error.message;
    verifyButton.disabled = false;
  }
});

reportButton.addEventListener("click", () => {
  if (orderId) {
    window.open(`/api/demo-orders/${orderId}/report`, "_blank", "noopener");
  }
});

prepareSession().catch(() => {
  formMessage.textContent = "Das lokale Demo-Portal konnte nicht initialisiert werden.";
  orderButton.disabled = true;
});
