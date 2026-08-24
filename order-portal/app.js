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
  verificationMessage.textContent = "Cockpit bereit · 3/3 geprüft";
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

const rentalCompany = document.querySelector("#rental-company");
const catalogGrid = document.querySelector("#catalog-grid");
const rentalList = document.querySelector("#rental-list");
const rentalMessage = document.querySelector("#rental-message");
const RENTAL_STORAGE_KEY = "aistudioxyz-kmu-rentals-v1";

let catalogAgents = [];
let rentalKeys = loadRentalKeys();

function loadRentalKeys() {
  try {
    const value = JSON.parse(localStorage.getItem(RENTAL_STORAGE_KEY) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

function persistRentalKeys() {
  try {
    localStorage.setItem(RENTAL_STORAGE_KEY, JSON.stringify(rentalKeys));
  } catch {
    // Rental actions still work for the current page if storage is disabled.
  }
}

function rentKeyFor(agentId) {
  if (!rentalKeys[`rent:${agentId}`]) {
    rentalKeys[`rent:${agentId}`] = operationKey(`rent-${agentId}`);
    persistRentalKeys();
  }
  return rentalKeys[`rent:${agentId}`];
}

function cancelKeyFor(rentalId) {
  if (!rentalKeys[`cancel:${rentalId}`]) {
    rentalKeys[`cancel:${rentalId}`] = operationKey(`cancel-${rentalId}`);
    persistRentalKeys();
  }
  return rentalKeys[`cancel:${rentalId}`];
}

function resetRentKey(agentId) {
  rentalKeys[`rent:${agentId}`] = operationKey(`rent-${agentId}`);
  persistRentalKeys();
}

function currentRentalCompany() {
  return (rentalCompany.value || companyInput.value || "").trim();
}

function renderCatalog() {
  catalogGrid.innerHTML = "";
  for (const agent of catalogAgents) {
    const card = document.createElement("article");
    card.className = "catalog-card";
    const title = document.createElement("h3");
    title.textContent = agent.label;
    const description = document.createElement("p");
    description.textContent = agent.description;
    const meta = document.createElement("div");
    meta.className = "catalog-meta";
    const price = document.createElement("span");
    price.className = "price";
    price.textContent = `${agent.monthly_price_eur} € / Monat`;
    const tag = document.createElement("span");
    tag.className = "provision-tag";
    tag.textContent = agent.provisionable
      ? "Wird lokal provisioniert"
      : "Katalog — Pack folgt";
    meta.append(price, tag);
    const button = document.createElement("button");
    button.className = "primary";
    button.type = "button";
    button.dataset.agentId = agent.agent_id;
    button.innerHTML = "<span>Mieten</span><span aria-hidden=\"true\">→</span>";
    button.addEventListener("click", () => rentAgent(agent.agent_id, button));
    card.append(title, description, meta, button);
    catalogGrid.append(card);
  }
}

function renderRentals(rentals) {
  rentalList.innerHTML = "";
  const active = (rentals || []).filter((item) => item.status === "active");
  if (!active.length) {
    const empty = document.createElement("p");
    empty.className = "rental-empty";
    empty.textContent = "Noch keine aktive Miete für diesen Mandanten.";
    rentalList.append(empty);
    return;
  }
  for (const rental of active) {
    const row = document.createElement("article");
    row.className = "rental-row";
    const copy = document.createElement("div");
    const title = document.createElement("b");
    const agent = catalogAgents.find((item) => item.agent_id === rental.agent_id);
    title.textContent = agent ? agent.label : rental.agent_id;
    const detail = document.createElement("small");
    const provision = rental.provisioned ? "Instanz aktiv" : "Ledger-only";
    detail.textContent = `${rental.monthly_price_eur} € · ${provision} · kündbar`;
    copy.append(title, detail);
    const status = document.createElement("span");
    status.className = "state ready";
    status.textContent = "Aktiv";
    const button = document.createElement("button");
    button.className = "secondary";
    button.type = "button";
    button.textContent = "Kündigen";
    button.addEventListener("click", () => cancelRental(rental, button));
    row.append(copy, status, button);
    rentalList.append(row);
  }
}

async function loadCatalog() {
  const payload = await api("/api/agents");
  catalogAgents = payload.agents || [];
  renderCatalog();
}

async function loadRentals() {
  const company = currentRentalCompany();
  if (!company) {
    renderRentals([]);
    return;
  }
  const query = new URLSearchParams({company_name: company});
  const payload = await api(`/api/rentals?${query.toString()}`);
  renderRentals(payload.rentals || []);
}

async function rentAgent(agentId, button) {
  const company = currentRentalCompany();
  if (!company) {
    rentalMessage.textContent = "Bitte zuerst einen Firmennamen angeben.";
    rentalCompany.focus();
    return;
  }
  if (!csrfToken) {
    rentalMessage.textContent = "Lokale Sitzung ist noch nicht bereit.";
    return;
  }
  button.disabled = true;
  rentalMessage.textContent = "Miete wird eingetragen …";
  try {
    await api("/api/rentals", {
      method: "POST",
      body: JSON.stringify({
        company_name: company,
        agent_id: agentId,
        display_name: company,
        idempotency_key: rentKeyFor(agentId)
      })
    });
    rentalMessage.textContent = "Miete aktiv — Listenpreis, keine Zahlung.";
    await loadRentals();
  } catch (error) {
    rentalMessage.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function cancelRental(rental, button) {
  const company = currentRentalCompany();
  if (!company) {
    rentalMessage.textContent = "Firmenname fehlt für die Kündigung.";
    return;
  }
  button.disabled = true;
  rentalMessage.textContent = "Kündigung wird gespeichert …";
  try {
    await api(`/api/rentals/${rental.rental_id}/cancel`, {
      method: "POST",
      body: JSON.stringify({
        company_name: company,
        tenant_id: rental.tenant_id,
        idempotency_key: cancelKeyFor(rental.rental_id)
      })
    });
    resetRentKey(rental.agent_id);
    rentalMessage.textContent = "Miete gekündigt.";
    await loadRentals();
  } catch (error) {
    rentalMessage.textContent = error.message;
    button.disabled = false;
  }
}

rentalCompany.addEventListener("change", () => {
  loadRentals().catch(() => {
    rentalMessage.textContent = "Mieten konnten nicht geladen werden.";
  });
});

const originalPrepare = prepareSession;
prepareSession = async function patchedPrepare() {
  await originalPrepare();
  if (stored.companyName && !rentalCompany.value) {
    rentalCompany.value = stored.companyName;
  }
  await loadCatalog();
  await loadRentals();
};


const previousShowReady = showReady;
showReady = function wrappedShowReady(order, scroll = false) {
  previousShowReady(order, scroll);
  if (!rentalCompany.value) {
    rentalCompany.value = companyInput.value;
  }
  loadRentals().catch(() => {});
};

if (stored.companyName && !rentalCompany.value) {
  rentalCompany.value = stored.companyName;
}
loadCatalog()
  .then(() => loadRentals())
  .catch(() => {
    rentalMessage.textContent = "Agentenkatalog konnte nicht geladen werden.";
  });
