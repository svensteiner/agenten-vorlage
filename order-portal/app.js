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
  const demoFold = document.querySelector("#zero-demo");
  if (demoFold) demoFold.open = true;
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
    card.className = agent.provisionable ? "catalog-card" : "catalog-card pending";
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
      ? "Wird lokal angelegt und lässt sich öffnen"
      : "Pack folgt — noch nicht öffenbar";
    meta.append(price, tag);
    const button = document.createElement("button");
    button.className = agent.provisionable ? "primary" : "secondary";
    button.type = "button";
    button.dataset.agentId = agent.agent_id;
    const rentLabel = agent.cta_label || (agent.provisionable ? "Mieten" : "Vormerken — Pack folgt");
    button.innerHTML = "<span>" + rentLabel + "</span><span aria-hidden=\"true\">→</span>";
    button.addEventListener("click", () => rentAgent(agent.agent_id, button));
    card.append(title, description, meta, button);
    catalogGrid.append(card);
  }
}

function renderRentals(rentals, snapshots) {
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
    const provision = rental.provisioned ? "Instanz aktiv" : "Ledger-only - Pack folgt";
    detail.textContent = rental.monthly_price_eur + " € · " + provision + " · kündbar";
    copy.append(title, detail);
    const snapshot = snapshots && snapshots[rental.rental_id];
    if (snapshot && snapshot.onboarding && snapshot.onboarding.supported) {
      const status = document.createElement("span");
      status.className = "onboard-status";
      if (snapshot.onboarding.status === "ready") {
        const mode = snapshot.onboarding.mode === "starter" ? "Musterdaten" : "Excel";
        status.textContent = "Onboarding: " + mode;
      } else {
        status.textContent = "Onboarding: Excel hochladen oder mit Muster starten";
      }
      copy.append(status);
    }
    const state = document.createElement("span");
    state.className = "state ready";
    state.textContent = "Aktiv";
    const actions = document.createElement("div");
    actions.className = "rental-actions";
    if (rental.provisioned) {
      const openButton = document.createElement("button");
      openButton.className = "primary";
      openButton.type = "button";
      openButton.textContent = "Öffnen";
      openButton.addEventListener("click", () => openRental(rental));
      actions.append(openButton);
      if (snapshot && snapshot.onboarding && snapshot.onboarding.supported) {
        const onboardWrap = document.createElement("div");
        onboardWrap.className = "onboard-actions";
        const excelButton = document.createElement("button");
        excelButton.className = "secondary";
        excelButton.type = "button";
        excelButton.textContent = "Excel hochladen";
        excelButton.addEventListener("click", () => pickExcel(rental));
        const starterButton = document.createElement("button");
        starterButton.className = "secondary";
        starterButton.type = "button";
        starterButton.textContent = "Mit Muster starten";
        starterButton.addEventListener("click", () => startStarter(rental, starterButton));
        onboardWrap.append(excelButton, starterButton);
        actions.append(onboardWrap);
      }
    } else {
      const hint = document.createElement("span");
      hint.className = "pack-hint";
      hint.textContent = "Pack folgt";
      actions.append(hint);
    }
    const button = document.createElement("button");
    button.className = "secondary";
    button.type = "button";
    button.textContent = "Kündigen";
    button.addEventListener("click", () => cancelRental(rental, button));
    actions.append(button);
    row.append(copy, state, actions);
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
  const rentals = payload.rentals || [];
  const snapshots = {};
  for (const rental of rentals) {
    if (rental.status !== "active" || !rental.provisioned) continue;
    try {
      const instanceQuery = new URLSearchParams({tenant_id: rental.tenant_id});
      snapshots[rental.rental_id] = await api(
        `/api/rentals/${rental.rental_id}/instance?${instanceQuery.toString()}`
      );
    } catch {
      // Snapshot is optional; Öffnen bleibt erreichbar.
    }
  }
  renderRentals(rentals, snapshots);
}

function bytesToBase64(bytes) {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

async function startStarter(rental, button) {
  const company = currentRentalCompany();
  if (!company) {
    rentalMessage.textContent = "Bitte zuerst einen Firmennamen angeben.";
    return;
  }
  button.disabled = true;
  rentalMessage.textContent = "Musterdaten werden in die Instanz gelegt.";
  try {
    await api(`/api/rentals/${rental.rental_id}/onboard`, {
      method: "POST",
      body: JSON.stringify({
        company_name: company,
        tenant_id: rental.tenant_id,
        mode: "starter",
        idempotency_key: operationKey("onboard-starter")
      })
    });
    rentalMessage.textContent = "Muster liegt in der Instanz — Öffnen.";
    await loadRentals();
  } catch (error) {
    rentalMessage.textContent = error.message;
    button.disabled = false;
  }
}

let excelTarget = null;

function pickExcel(rental) {
  excelTarget = rental;
  const input = document.querySelector("#rental-excel");
  if (!input) {
    rentalMessage.textContent = "Excel-Auswahl ist nicht verfügbar.";
    return;
  }
  input.value = "";
  input.click();
}

async function uploadExcelFile(file) {
  const rental = excelTarget;
  excelTarget = null;
  const company = currentRentalCompany();
  if (!rental || !company) {
    rentalMessage.textContent = "Miete oder Firmenname fehlt.";
    return;
  }
  if (!file || !/\.xlsx$/i.test(file.name)) {
    rentalMessage.textContent = "Bitte eine XLSX-Datei wählen.";
    return;
  }
  rentalMessage.textContent = "Excel wird unverändert in die Instanz kopiert.";
  const buffer = new Uint8Array(await file.arrayBuffer());
  await api(`/api/rentals/${rental.rental_id}/onboard`, {
    method: "POST",
    body: JSON.stringify({
      company_name: company,
      tenant_id: rental.tenant_id,
      mode: "excel",
      filename: file.name.replace(/^.*[\\/]/, ""),
      content_base64: bytesToBase64(buffer),
      idempotency_key: operationKey("onboard-excel")
    })
  });
  rentalMessage.textContent = "Excel liegt in der Instanz - Formeln unangetastet.";
  await loadRentals();
}

const excelInput = document.querySelector("#rental-excel");
if (excelInput) {
  excelInput.addEventListener("change", async (event) => {
    const file = event.target.files && event.target.files[0];
    try {
      await uploadExcelFile(file);
    } catch (error) {
      rentalMessage.textContent = error.message;
    }
  });
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
    const rental = await api("/api/rentals", {
      method: "POST",
      body: JSON.stringify({
        company_name: company,
        agent_id: agentId,
        display_name: company,
        idempotency_key: rentKeyFor(agentId)
      })
    });
    if (rental && rental.provisioned) {
      rentalMessage.textContent = "Instanz bereit — Öffnen";
    } else {
      rentalMessage.textContent = "Vorgemerkt — Pack folgt, noch nicht öffenbar. Listenpreis, keine Zahlung.";
    }
    await loadRentals();
  } catch (error) {
    rentalMessage.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}


function openRental(rental) {
  const tenantId = rental && rental.tenant_id;
  const rentalId = rental && rental.rental_id;
  if (!tenantId || !rentalId) {
    rentalMessage.textContent = "Miete kann nicht geöffnet werden.";
    return;
  }
  const query = new URLSearchParams({tenant_id: tenantId});
  window.open(
    `/api/rentals/${rentalId}/open?${query.toString()}`,
    "_blank",
    "noopener"
  );
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
