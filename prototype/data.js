/*
 * Meridian Industrie GmbH — fiktive Demo-Firma für den AI-Studio-Prototyp.
 * ALLE Daten sind erfunden. Keine echten Kundendaten.
 *
 * Diese Datei ist die einzige Quelle der Wahrheit für Dokumente und Szenarien.
 * app.js rendert nur, was hier steht. Neue Dokumente/Szenarien = nur hier ergänzen.
 */

const COMPANY = {
  name: "Meridian Industrie GmbH",
  tagline: "Maschinen- & Anlagenbau · München",
  facts: [
    { label: "Gegründet", value: "1971" },
    { label: "Mitarbeitende", value: "2.412" },
    { label: "Standorte", value: "München · Werk 2 Ingolstadt · Logistik Nürnberg" },
    { label: "Umsatz 2025", value: "612 Mio. €" },
  ],
  people: {
    ceo: "Markus Brandt",
    cfo: "Dr. Katharina Vogel",
    hr: "Sabine Reuter",
    procurement: "Thomas Krüger",
    legal: "Dr. Elena Wagner",
    audit: "Frank Hoffmann",
  },
};

// Module in der Seitenleiste. `key` verbindet Dokumente & Szenarien mit dem Modul.
const MODULES = [
  { key: "wissen", label: "Wissen", icon: "◆", hint: "Frag alles über dein Unternehmenswissen" },
  { key: "finanzen", label: "Finanzen", icon: "€", hint: "Rechnungen, Kosten, Quartalszahlen" },
  { key: "audit", label: "Audit", icon: "✓", hint: "Belege, Nachweise, Compliance" },
  { key: "hr", label: "HR", icon: "☺", hint: "Richtlinien, Verträge, Personal" },
  { key: "vertraege", label: "Verträge", icon: "§", hint: "Laufzeiten, Verlängerungen, Klauseln" },
  { key: "berichte", label: "Berichte", icon: "▤", hint: "Projekte, Vorstand, ESG" },
  { key: "einstellungen", label: "Einstellungen", icon: "⚙", hint: "Datenquellen & Konfiguration" },
];

// --- Dokumentenbibliothek --------------------------------------------------
// snippet: Vorschautext. body: Absätze fürs Dokumentenviewer (highlight=true hebt hervor).
const DOCS = {
  "reiserichtlinie-2026": {
    id: "reiserichtlinie-2026",
    title: "Reiserichtlinie 2026",
    type: "Richtlinie",
    module: "hr",
    path: "SharePoint › HR › Richtlinien › Reiserichtlinie_2026_v3.pdf",
    author: "Sabine Reuter (Leiterin HR)",
    date: "2026-01-15",
    updated: "gültig ab 01.02.2026",
    snippet: "Verbindliche Regeln für Dienstreisen: Buchung, Klassen, Verpflegung, Abrechnung.",
    body: [
      { t: "Reiserichtlinie 2026 der Meridian Industrie GmbH — gültig ab 1. Februar 2026. Ersetzt die Fassung 2024.", highlight: false },
      { t: "§2 Bahnreisen: Fahrten ab 3 Stunden Reisezeit dürfen in der 1. Klasse gebucht werden. Kürzere Fahrten in der 2. Klasse.", highlight: true },
      { t: "§3 Flugreisen: Economy Class ist Standard. Business Class nur bei Flügen über 6 Stunden und mit Freigabe der Bereichsleitung.", highlight: true },
      { t: "§4 Übernachtung: Der erstattungsfähige Hotelhöchstsatz beträgt 140 € pro Nacht (Inland) bzw. 180 € (Ausland).", highlight: true },
      { t: "§5 Verpflegungspauschale: 28 € pro vollem Reisetag, 14 € für An- und Abreisetage, gemäß gesetzlicher Pauschale.", highlight: false },
      { t: "§7 Buchung: Alle Reisen sind über das Reiseportal (Concur) mindestens 7 Tage im Voraus zu buchen.", highlight: false },
    ],
  },
  "q1-bericht-2026": {
    id: "q1-bericht-2026",
    title: "Quartalsbericht Q1 2026",
    type: "Finanzbericht",
    module: "finanzen",
    path: "Fileserver › Controlling › 2026 › Quartalsbericht_Q1_2026.xlsx",
    author: "Dr. Katharina Vogel (CFO)",
    date: "2026-04-10",
    snippet: "Materialkostenanstieg von 18,4 % ggü. Vorjahr, getrieben durch Stahlpreise.",
    body: [
      { t: "Quartalsbericht Q1 2026 — Meridian Industrie GmbH, Bereich Controlling.", highlight: false },
      { t: "Die Materialkosten stiegen im Q1 2026 um 18,4 % gegenüber Q1 2025 (von 41,2 Mio. € auf 48,8 Mio. €).", highlight: true },
      { t: "Haupttreiber ist der Stahleinkauf: Der Tonnenpreis für Baustahl S355 stieg von 780 € auf 920 € (+17,9 %), bedingt durch Energiekosten und Lieferengpässe.", highlight: true },
      { t: "Der Lieferant Stahlwerk Donau AG hat zum 01.03.2026 eine Preisanpassung von 15 % durchgesetzt (Rahmenvertrag RV-2023-014, Preisgleitklausel §6).", highlight: true },
      { t: "Gegenmaßnahme: Der Einkauf verhandelt einen Zweitlieferanten (Ferro Nord) zur Reduktion der Abhängigkeit. Erwartete Entlastung ab Q3 2026.", highlight: false },
      { t: "Rohertragsmarge sank folglich von 34,1 % auf 31,6 %. Umsatz stabil bei 158 Mio. €.", highlight: false },
    ],
  },
  "rechnung-2026-1843": {
    id: "rechnung-2026-1843",
    title: "Rechnung 2026-1843",
    type: "Eingangsrechnung",
    module: "finanzen",
    path: "SAP › FI › Belege › 2026 › ER_2026-1843.pdf",
    author: "Stahlwerk Donau AG (Lieferant)",
    date: "2026-03-22",
    snippet: "Lieferung Baustahl S355 · 87.584 € brutto · Bestellbezug PO-2026-0512.",
    body: [
      { t: "Rechnung Nr. 2026-1843 — Stahlwerk Donau AG an Meridian Industrie GmbH.", highlight: false },
      { t: "Position: 80 t Baustahl S355, Preis 920 €/t = 73.600 € netto.", highlight: true },
      { t: "Umsatzsteuer 19 %: 13.984 €. Rechnungsbetrag brutto: 87.584 €.", highlight: true },
      { t: "Bestellbezug: PO-2026-0512. Lieferung erfolgt am 20.03.2026, Werk 2 Ingolstadt.", highlight: true },
      { t: "Zahlungsziel: 30 Tage netto, 2 % Skonto bei Zahlung innerhalb 14 Tagen.", highlight: false },
    ],
    lineItems: {
      doc: "Rechnung 2026-1843",
      ref: "Bestellbezug PO-2026-0512",
      rows: [
        { pos: "1", desc: "Baustahl S355, Warmband — Materialzeugnis 3.1 (EN 10204)", qty: "80,000 t", unit: "920,00 €", sum: "73.600,00 €" },
      ],
      net: "73.600,00 €",
      vatRate: "19 %",
      vat: "13.984,00 €",
      gross: "87.584,00 €",
    },
  },
  "bestellung-po-2026-0512": {
    id: "bestellung-po-2026-0512",
    title: "Bestellung PO-2026-0512",
    type: "Bestellung",
    module: "finanzen",
    path: "SAP › MM › Bestellungen › PO-2026-0512.pdf",
    author: "Thomas Krüger (Einkauf)",
    date: "2026-03-05",
    snippet: "80 t Baustahl S355 bei Stahlwerk Donau AG · genehmigt.",
    body: [
      { t: "Bestellung PO-2026-0512 — Meridian Industrie GmbH an Stahlwerk Donau AG.", highlight: false },
      { t: "Bestellmenge: 80 t Baustahl S355 zu 920 €/t = 73.600 € netto.", highlight: true },
      { t: "Freigabe: Thomas Krüger (Einkaufsleiter) am 05.03.2026, Kostenstelle Werk 2 / Projekt Alpha.", highlight: true },
      { t: "Liefertermin vereinbart: 20.03.2026, Werk 2 Ingolstadt.", highlight: false },
    ],
    lineItems: {
      doc: "Bestellung PO-2026-0512",
      ref: "Kostenstelle Werk 2 / Projekt Alpha",
      rows: [
        { pos: "1", desc: "Baustahl S355, Warmband — Liefertermin 20.03.2026", qty: "80,000 t", unit: "920,00 €", sum: "73.600,00 €" },
      ],
      net: "73.600,00 €",
    },
  },
  "wareneingang-we-2026-0778": {
    id: "wareneingang-we-2026-0778",
    title: "Wareneingang WE-2026-0778",
    type: "Wareneingang",
    module: "audit",
    path: "SAP › MM › Wareneingänge › WE-2026-0778.pdf",
    author: "Lager Werk 2 (automatisch erfasst)",
    date: "2026-03-20",
    snippet: "80 t Baustahl S355 vollständig eingegangen · Bestellbezug PO-2026-0512.",
    body: [
      { t: "Wareneingangsbeleg WE-2026-0778 — Werk 2 Ingolstadt.", highlight: false },
      { t: "Eingang: 80 t Baustahl S355 am 20.03.2026, geprüft durch Wareneingangskontrolle.", highlight: true },
      { t: "Bestellbezug: PO-2026-0512. Menge stimmt mit Bestellung überein, keine Abweichung.", highlight: true },
      { t: "Qualitätsprüfung: bestanden (Materialzeugnis 3.1 nach EN 10204 liegt vor).", highlight: false },
    ],
    lineItems: {
      doc: "Wareneingang WE-2026-0778",
      ref: "Bestellbezug PO-2026-0512 · keine Abweichung",
      rows: [
        { pos: "1", desc: "Baustahl S355, Warmband — Qualitätsprüfung bestanden", qty: "80,000 t", unit: "—", sum: "vollständig" },
      ],
    },
  },
  "rahmenvertrag-stahlwerk-donau": {
    id: "rahmenvertrag-stahlwerk-donau",
    title: "Rahmenvertrag Stahlwerk Donau AG",
    type: "Rahmenvertrag",
    module: "vertraege",
    path: "SharePoint › Recht › Verträge › RV-2023-014_Stahlwerk_Donau.pdf",
    author: "Dr. Elena Wagner (Recht)",
    date: "2023-06-01",
    snippet: "Liefervertrag Baustahl · automatische Verlängerung um 12 Monate · Preisgleitklausel.",
    body: [
      { t: "Rahmenvertrag RV-2023-014 zwischen Meridian Industrie GmbH und Stahlwerk Donau AG.", highlight: false },
      { t: "§9 Laufzeit: Der Vertrag läuft bis 31.05.2026 und verlängert sich automatisch um jeweils 12 Monate, sofern nicht 3 Monate vor Ablauf schriftlich gekündigt wird.", highlight: true },
      { t: "§6 Preisgleitklausel: Der Lieferant darf Preise bei Rohstoff- oder Energiekostensteigerungen von mehr als 10 % anpassen.", highlight: true },
      { t: "Nächste Kündigungsfrist: 28.02.2026. Bei Nichtkündigung Verlängerung bis 31.05.2027.", highlight: true },
    ],
  },
  "wartungsvertrag-siemens": {
    id: "wartungsvertrag-siemens",
    title: "Wartungsvertrag Siemens",
    type: "Wartungsvertrag",
    module: "vertraege",
    path: "SharePoint › Recht › Verträge › WV-2022-041_Siemens.pdf",
    author: "Dr. Elena Wagner (Recht)",
    date: "2022-09-01",
    snippet: "Wartung Fertigungsanlagen · automatische Verlängerung um 24 Monate.",
    body: [
      { t: "Wartungsvertrag WV-2022-041 zwischen Meridian Industrie GmbH und Siemens AG.", highlight: false },
      { t: "§8 Laufzeit: Erstlaufzeit bis 31.08.2026, danach automatische Verlängerung um jeweils 24 Monate.", highlight: true },
      { t: "Kündigungsfrist: 6 Monate zum Laufzeitende. Nächster Kündigungstermin: 28.02.2026.", highlight: true },
    ],
  },
  "lizenzvertrag-sap": {
    id: "lizenzvertrag-sap",
    title: "Lizenzvertrag SAP S/4HANA",
    type: "Lizenzvertrag",
    module: "vertraege",
    path: "SharePoint › Recht › Verträge › LV-2021-007_SAP.pdf",
    author: "Dr. Elena Wagner (Recht)",
    date: "2021-11-01",
    snippet: "ERP-Lizenzen · automatische Verlängerung um 12 Monate · 1.100 Nutzer.",
    body: [
      { t: "Lizenzvertrag LV-2021-007 zwischen Meridian Industrie GmbH und SAP SE.", highlight: false },
      { t: "§11 Laufzeit: 12 Monate, automatische Verlängerung um jeweils weitere 12 Monate ohne fristgerechte Kündigung (3 Monate).", highlight: true },
      { t: "Nächster Kündigungstermin: 31.07.2026. Lizenzvolumen: 1.100 Named User.", highlight: true },
    ],
  },
  "mietvertrag-logistik": {
    id: "mietvertrag-logistik",
    title: "Mietvertrag Logistikzentrum Nürnberg",
    type: "Mietvertrag",
    module: "vertraege",
    path: "SharePoint › Recht › Verträge › MV-2024-003_Logistik_Nuernberg.pdf",
    author: "Dr. Elena Wagner (Recht)",
    date: "2024-01-01",
    snippet: "Feste Laufzeit bis 2029 · KEINE automatische Verlängerung.",
    body: [
      { t: "Mietvertrag MV-2024-003 für das Logistikzentrum Nürnberg.", highlight: false },
      { t: "§4 Laufzeit: Feste Laufzeit bis 31.12.2029. Keine automatische Verlängerung; eine Anschlussmietung bedarf einer neuen Vereinbarung.", highlight: true },
    ],
  },
  "projekt-alpha-status": {
    id: "projekt-alpha-status",
    title: "Projekt Alpha — Statusbericht",
    type: "Projektbericht",
    module: "berichte",
    path: "Fileserver › Projekte › Alpha › Statusbericht_2026-03.docx",
    author: "Projektleitung Alpha (Ing. Petra Lang)",
    date: "2026-03-31",
    snippet: "Neue Fertigungslinie Werk 2 · Budget 24 Mio. € · Inbetriebnahme Q4 2026.",
    body: [
      { t: "Projekt Alpha — Aufbau einer neuen automatisierten Fertigungslinie in Werk 2 Ingolstadt.", highlight: false },
      { t: "Ziel: Kapazitätserhöhung um 35 % bei Getriebekomponenten. Gesamtbudget: 24 Mio. €.", highlight: true },
      { t: "Status per 31.03.2026: 62 % abgeschlossen, im Zeitplan. Bislang 14,1 Mio. € verausgabt.", highlight: true },
      { t: "Risiken: Stahlpreisanstieg belastet das Materialbudget (+0,9 Mio. € erwartet, siehe Q1-Bericht). Liefertermin Robotik-Zellen um 3 Wochen verschoben.", highlight: true },
      { t: "Meilenstein: Geplante Inbetriebnahme Q4 2026. Abnahmetests ab Oktober.", highlight: false },
    ],
  },
  "vorstandsprotokoll-2026-03": {
    id: "vorstandsprotokoll-2026-03",
    title: "Vorstandsprotokoll März 2026",
    type: "Sitzungsprotokoll",
    module: "berichte",
    path: "SharePoint › Vorstand › Protokolle › Protokoll_2026-03.pdf",
    author: "Markus Brandt (CEO)",
    date: "2026-03-28",
    snippet: "Beschlüsse zu Zweitlieferant, Projekt Alpha und ESG-Zielen.",
    body: [
      { t: "Vorstandssitzung Meridian Industrie GmbH, 28.03.2026.", highlight: false },
      { t: "TOP 1: Materialkosten. Der Vorstand beschließt die Aufnahme von Ferro Nord als Zweitlieferant zur Reduktion der Stahlpreis-Abhängigkeit.", highlight: true },
      { t: "TOP 2: Projekt Alpha bleibt im Zeitplan; Vorstand genehmigt Mehrbudget von 0,9 Mio. € für Materialpreissteigerung.", highlight: true },
      { t: "TOP 3: ESG-Ziel bekräftigt — 30 % CO₂-Reduktion bis 2030 gegenüber 2020.", highlight: false },
    ],
  },
  "brandschutzordnung-werk2": {
    id: "brandschutzordnung-werk2",
    title: "Brandschutzordnung Werk 2",
    type: "Sicherheitsdokument",
    module: "audit",
    path: "SharePoint › Arbeitssicherheit › Werk2 › Brandschutzordnung_Teil_B.pdf",
    author: "Fachkraft Arbeitssicherheit (M. Ostermann)",
    date: "2025-11-12",
    snippet: "Brandschutzordnung nach DIN 14096, Teil A/B/C · Werk 2 Ingolstadt.",
    body: [
      { t: "Brandschutzordnung Werk 2 Ingolstadt nach DIN 14096 (Teil A, B und C).", highlight: false },
      { t: "Teil B §3: Flucht- und Rettungswege sind freizuhalten; Brandschutztüren stets geschlossen halten.", highlight: true },
      { t: "Teil B §5: Sammelplatz bei Alarm ist Parkplatz Nord. Räumung über die gekennzeichneten Notausgänge.", highlight: true },
      { t: "Brandschutzbeauftragter: M. Ostermann, erreichbar unter Durchwahl -412.", highlight: false },
    ],
  },
  "feuerbeschau-2025": {
    id: "feuerbeschau-2025",
    title: "Feuerbeschau-Protokoll Werk 2",
    type: "Prüfnachweis",
    module: "audit",
    path: "Fileserver › Arbeitssicherheit › Nachweise › Feuerbeschau_Werk2_2025.pdf",
    author: "Feuerwehr Ingolstadt (behördlich)",
    date: "2025-10-08",
    snippet: "Behördliche Feuerbeschau bestanden · keine wesentlichen Mängel.",
    body: [
      { t: "Protokoll der behördlichen Feuerbeschau Werk 2 Ingolstadt, 08.10.2025.", highlight: false },
      { t: "Ergebnis: Bestanden. Flucht- und Rettungswege, Löschmittel und Brandmeldeanlage in Ordnung.", highlight: true },
      { t: "Auflage: Nachrüstung eines Rauchmelders in Lagerhalle C bis 31.12.2025 (erledigt am 03.12.2025).", highlight: true },
    ],
  },
  "esg-bericht-2025": {
    id: "esg-bericht-2025",
    title: "ESG-Bericht 2025",
    type: "Nachhaltigkeitsbericht",
    module: "berichte",
    path: "SharePoint › Vorstand › ESG › ESG_Bericht_2025.pdf",
    author: "Nachhaltigkeitsteam",
    date: "2026-02-20",
    snippet: "CO₂-Bilanz, Energie, Lieferkette · Fortschritt gegen Ziel 2030.",
    body: [
      { t: "ESG-Bericht 2025 der Meridian Industrie GmbH nach CSRD/ESRS.", highlight: false },
      { t: "CO₂-Emissionen 2025: 41.200 t (Scope 1+2), -12 % ggü. 2020. Ziel: -30 % bis 2030.", highlight: true },
      { t: "Anteil erneuerbarer Energie am Strombezug: 68 %. Photovoltaik Werk 2 seit Q3 2025 aktiv.", highlight: true },
    ],
  },
};

// --- Szenarien -------------------------------------------------------------
// Jedes Szenario: Frage → strukturierte Antwort. `keywords` steuert das
// Matching bei frei getippten Fragen. `confidence` 0..100.
const SCENARIOS = [
  {
    id: "reiserichtlinie",
    module: "hr",
    question: "Wo finde ich die aktuelle Reiserichtlinie?",
    keywords: ["reise", "reiserichtlinie", "dienstreise", "travel", "bahn", "hotel", "flug", "spesen"],
    answer: {
      text: "Die aktuelle <b>Reiserichtlinie 2026</b> ist seit dem <b>1. Februar 2026</b> gültig und liegt in SharePoint unter <i>HR › Richtlinien</i>. Die wichtigsten Regeln:<ul><li><b>Bahn:</b> 1. Klasse ab 3 Stunden Reisezeit, sonst 2. Klasse.</li><li><b>Flug:</b> Economy Standard, Business nur ab 6 Stunden mit Freigabe.</li><li><b>Hotel:</b> max. 140 €/Nacht Inland, 180 € Ausland.</li><li><b>Verpflegung:</b> 28 € pro vollem Reisetag.</li></ul>Buchung über Concur, mindestens 7 Tage im Voraus.",
      reasoning: [
        "Anfrage als HR-Richtlinien-Frage erkannt.",
        "Dokumententyp „Richtlinie\" im Modul HR durchsucht.",
        "Neueste gültige Version identifiziert (2026 ersetzt 2024).",
        "Kernregeln aus §2–§5 extrahiert und zusammengefasst.",
      ],
      sources: [
        { docId: "reiserichtlinie-2026", relevance: 98, quote: "Fahrten ab 3 Stunden Reisezeit dürfen in der 1. Klasse gebucht werden." },
      ],
      confidence: 98,
      related: ["reiserichtlinie-2026"],
      followups: ["Wie hoch ist die Verpflegungspauschale?", "Wer muss Business-Class-Flüge freigeben?"],
    },
  },
  {
    id: "materialkosten",
    module: "finanzen",
    question: "Warum sind die Materialkosten gestiegen?",
    keywords: ["material", "materialkosten", "kosten gestiegen", "stahl", "preis", "teurer", "marge"],
    answer: {
      text: "Die Materialkosten stiegen im <b>Q1 2026 um 18,4 %</b> (von 41,2 auf 48,8 Mio. €). Hauptursache ist der <b>Stahleinkauf</b>:<ul><li>Der Tonnenpreis für Baustahl S355 stieg von 780 € auf <b>920 € (+17,9 %)</b> — bedingt durch Energiekosten und Lieferengpässe.</li><li>Der Lieferant <b>Stahlwerk Donau AG</b> hat über die Preisgleitklausel (§6 des Rahmenvertrags) zum 01.03.2026 eine Preisanpassung von 15 % durchgesetzt.</li></ul>Die Rohertragsmarge sank dadurch von 34,1 % auf 31,6 %. Gegenmaßnahme: Aufnahme des Zweitlieferanten Ferro Nord, Entlastung ab Q3 2026.",
      reasoning: [
        "Frage als Kostenanalyse im Modul Finanzen eingeordnet.",
        "Quartalsbericht Q1 2026 als primäre Quelle gefunden.",
        "Ursache über Lineage zum Rahmenvertrag (Preisgleitklausel) und zur Beispielrechnung verknüpft.",
        "Zahlen gegengeprüft: Bericht ↔ Rechnung 2026-1843 (920 €/t stimmen überein).",
      ],
      sources: [
        { docId: "q1-bericht-2026", relevance: 96, quote: "Die Materialkosten stiegen im Q1 2026 um 18,4 % gegenüber Q1 2025." },
        { docId: "rahmenvertrag-stahlwerk-donau", relevance: 82, quote: "Der Lieferant darf Preise bei Rohstoff- oder Energiekostensteigerungen von mehr als 10 % anpassen." },
        { docId: "rechnung-2026-1843", relevance: 74, quote: "80 t Baustahl S355, Preis 920 €/t = 73.600 € netto." },
      ],
      confidence: 94,
      related: ["q1-bericht-2026", "rahmenvertrag-stahlwerk-donau", "rechnung-2026-1843"],
      followups: ["Welche Gegenmaßnahmen sind geplant?", "Zeig mir den Rahmenvertrag mit Stahlwerk Donau."],
    },
  },
  {
    id: "beleg-rechnung",
    module: "audit",
    question: "Zeig mir die Belege zu Rechnung 2026-1843.",
    keywords: ["beleg", "rechnung 2026-1843", "1843", "nachweis", "prüfung", "three-way", "abgleich"],
    answer: {
      text: "Für <b>Rechnung 2026-1843</b> (Stahlwerk Donau AG, 87.584 € brutto) liegt ein vollständiger <b>Drei-Wege-Abgleich</b> vor:<ul><li><b>Bestellung PO-2026-0512</b> — 80 t Baustahl zu 920 €/t, freigegeben von Thomas Krüger.</li><li><b>Wareneingang WE-2026-0778</b> — 80 t am 20.03.2026 geprüft eingegangen, keine Abweichung.</li><li><b>Rechnung 2026-1843</b> — 80 t × 920 € = 73.600 € netto.</li></ul><b>Ergebnis:</b> Menge, Preis und Lieferung stimmen über alle drei Belege überein. Der Beleg ist prüfungssicher.",
      reasoning: [
        "Rechnungsnummer als Prüfvorgang im Modul Audit erkannt.",
        "Zugehörige Belege über den Bestellbezug PO-2026-0512 verknüpft.",
        "Drei-Wege-Abgleich durchgeführt: Bestellung ↔ Wareneingang ↔ Rechnung.",
        "Beträge und Mengen auf Übereinstimmung geprüft — keine Abweichung.",
      ],
      sources: [
        { docId: "rechnung-2026-1843", relevance: 99, quote: "Position: 80 t Baustahl S355, Preis 920 €/t = 73.600 € netto." },
        { docId: "bestellung-po-2026-0512", relevance: 95, quote: "Bestellmenge: 80 t Baustahl S355 zu 920 €/t = 73.600 € netto." },
        { docId: "wareneingang-we-2026-0778", relevance: 93, quote: "Menge stimmt mit Bestellung überein, keine Abweichung." },
      ],
      confidence: 97,
      related: ["rechnung-2026-1843", "bestellung-po-2026-0512", "wareneingang-we-2026-0778"],
      followups: ["Wurde das Skonto genutzt?", "Auf welche Kostenstelle wurde gebucht?"],
    },
  },
  {
    id: "projekt-alpha",
    module: "berichte",
    question: "Fasse Projekt Alpha zusammen.",
    keywords: ["projekt alpha", "alpha", "fertigungslinie", "projektstatus", "projekt zusammenfassen"],
    answer: {
      text: "<b>Projekt Alpha</b> ist der Aufbau einer neuen automatisierten Fertigungslinie in <b>Werk 2 Ingolstadt</b>.<ul><li><b>Ziel:</b> +35 % Kapazität bei Getriebekomponenten.</li><li><b>Budget:</b> 24 Mio. € (14,1 Mio. € verausgabt).</li><li><b>Status:</b> 62 % abgeschlossen, im Zeitplan (Stand 31.03.2026).</li><li><b>Risiken:</b> Stahlpreisanstieg belastet das Materialbudget (+0,9 Mio. €); Robotik-Zellen um 3 Wochen verschoben.</li><li><b>Inbetriebnahme:</b> geplant Q4 2026, Abnahmetests ab Oktober.</li></ul>Der Vorstand hat das Mehrbudget von 0,9 Mio. € bereits genehmigt.",
      reasoning: [
        "Projektname erkannt; Statusbericht als primäre Quelle geladen.",
        "Kennzahlen (Budget, Fortschritt, Termine) extrahiert.",
        "Risiko „Materialkosten\" mit dem Q1-Bericht und dem Vorstandsbeschluss verknüpft.",
        "Genehmigungsstatus aus dem Vorstandsprotokoll ergänzt.",
      ],
      sources: [
        { docId: "projekt-alpha-status", relevance: 97, quote: "Status per 31.03.2026: 62 % abgeschlossen, im Zeitplan." },
        { docId: "vorstandsprotokoll-2026-03", relevance: 79, quote: "Vorstand genehmigt Mehrbudget von 0,9 Mio. € für Materialpreissteigerung." },
      ],
      confidence: 93,
      related: ["projekt-alpha-status", "vorstandsprotokoll-2026-03", "q1-bericht-2026"],
      followups: ["Welche Risiken bestehen für Projekt Alpha?", "Wann ist die Inbetriebnahme geplant?"],
    },
  },
  {
    id: "vertraege-verlaengerung",
    module: "vertraege",
    question: "Finde alle Verträge mit automatischer Verlängerung.",
    keywords: ["vertrag", "verträge", "verlängerung", "automatisch", "kündigung", "laufzeit", "renewal"],
    answer: {
      text: "Es gibt <b>3 Verträge mit automatischer Verlängerung</b> — zwei davon mit <b>dringender Kündigungsfrist am 28.02.2026</b>:<table><tr><th>Vertrag</th><th>Verlängerung</th><th>Kündigung bis</th></tr><tr><td>Rahmenvertrag Stahlwerk Donau</td><td>+12 Monate</td><td><b>28.02.2026 ⚠</b></td></tr><tr><td>Wartungsvertrag Siemens</td><td>+24 Monate</td><td><b>28.02.2026 ⚠</b></td></tr><tr><td>Lizenzvertrag SAP</td><td>+12 Monate</td><td>31.07.2026</td></tr></table>Zum Vergleich: Der <b>Mietvertrag Logistikzentrum Nürnberg</b> hat eine feste Laufzeit bis 2029 <b>ohne</b> automatische Verlängerung.",
      reasoning: [
        "Anfrage als Vertragsklausel-Suche im Modul Verträge erkannt.",
        "Alle Verträge nach Verlängerungsklauseln durchsucht.",
        "3 Treffer mit Auto-Verlängerung, 1 Gegenbeispiel ohne.",
        "Kündigungsfristen berechnet und nach Dringlichkeit sortiert.",
      ],
      sources: [
        { docId: "rahmenvertrag-stahlwerk-donau", relevance: 94, quote: "verlängert sich automatisch um jeweils 12 Monate, sofern nicht 3 Monate vor Ablauf gekündigt wird." },
        { docId: "wartungsvertrag-siemens", relevance: 92, quote: "automatische Verlängerung um jeweils 24 Monate." },
        { docId: "lizenzvertrag-sap", relevance: 90, quote: "automatische Verlängerung um jeweils weitere 12 Monate ohne fristgerechte Kündigung." },
      ],
      confidence: 96,
      related: ["rahmenvertrag-stahlwerk-donau", "wartungsvertrag-siemens", "lizenzvertrag-sap", "mietvertrag-logistik"],
      followups: ["Welche Kündigungsfrist ist am dringendsten?", "Zeig mir den SAP-Lizenzvertrag."],
    },
  },
  {
    id: "vorstand-summary",
    module: "berichte",
    question: "Erstelle eine Zusammenfassung für den Vorstand.",
    keywords: ["vorstand", "zusammenfassung", "board", "management summary", "überblick", "briefing"],
    answer: {
      text: "<b>Vorstands-Kurzbriefing — Stand März 2026</b><ul><li><b>Finanzen:</b> Materialkosten +18,4 % (Stahl), Marge auf 31,6 % gesunken. Gegenmaßnahme Zweitlieferant Ferro Nord beschlossen.</li><li><b>Projekt Alpha:</b> im Zeitplan, 62 % fertig, Inbetriebnahme Q4 2026. Mehrbudget 0,9 Mio. € genehmigt.</li><li><b>Verträge:</b> Achtung — 2 Verträge (Stahlwerk Donau, Siemens) mit Kündigungsfrist 28.02.2026.</li><li><b>Compliance:</b> Feuerbeschau Werk 2 bestanden, Auflage erledigt.</li><li><b>ESG:</b> CO₂ -12 % ggü. 2020, auf Kurs zum Ziel -30 % bis 2030.</li></ul>",
      reasoning: [
        "Anfrage als bereichsübergreifende Management-Zusammenfassung erkannt.",
        "Kernaussagen aus Finanzen, Projekten, Verträgen, Audit und ESG aggregiert.",
        "Nur freigegebene, aktuelle Dokumente berücksichtigt.",
        "Handlungsrelevante Punkte (Kündigungsfristen) hervorgehoben.",
      ],
      sources: [
        { docId: "q1-bericht-2026", relevance: 88, quote: "Materialkosten stiegen um 18,4 %." },
        { docId: "projekt-alpha-status", relevance: 85, quote: "62 % abgeschlossen, im Zeitplan." },
        { docId: "vorstandsprotokoll-2026-03", relevance: 83, quote: "Aufnahme von Ferro Nord als Zweitlieferant." },
        { docId: "esg-bericht-2025", relevance: 71, quote: "CO₂-Emissionen 2025: -12 % ggü. 2020." },
      ],
      confidence: 91,
      related: ["q1-bericht-2026", "projekt-alpha-status", "vorstandsprotokoll-2026-03", "esg-bericht-2025", "rahmenvertrag-stahlwerk-donau"],
      followups: ["Welche Verträge muss ich jetzt kündigen?", "Wie steht es um die ESG-Ziele?"],
    },
  },
  {
    id: "brandschutz",
    module: "audit",
    question: "Wo ist die Brandschutzdokumentation für Werk 2?",
    keywords: ["brandschutz", "feuer", "sicherheit", "feuerbeschau", "rettungsweg", "din 14096", "werk 2"],
    answer: {
      text: "Für <b>Werk 2 Ingolstadt</b> liegen zwei zentrale Brandschutzdokumente vor:<ul><li><b>Brandschutzordnung Werk 2</b> (nach DIN 14096, Teil A/B/C) — Flucht- und Rettungswege, Sammelplatz Parkplatz Nord, Brandschutzbeauftragter M. Ostermann (-412).</li><li><b>Feuerbeschau-Protokoll 2025</b> — behördliche Prüfung am 08.10.2025 <b>bestanden</b>; Auflage (Rauchmelder Halle C) am 03.12.2025 erledigt.</li></ul>Beide Dokumente sind aktuell und prüfungsrelevant.",
      reasoning: [
        "Anfrage als Sicherheits-/Compliance-Frage für einen Standort erkannt.",
        "Dokumente nach Standort „Werk 2\" gefiltert.",
        "Richtlinie (Brandschutzordnung) und Nachweis (Feuerbeschau) zugeordnet.",
        "Aktualität und Auflagen-Status geprüft.",
      ],
      sources: [
        { docId: "brandschutzordnung-werk2", relevance: 95, quote: "Brandschutzordnung Werk 2 Ingolstadt nach DIN 14096 (Teil A, B und C)." },
        { docId: "feuerbeschau-2025", relevance: 90, quote: "Ergebnis: Bestanden. Flucht- und Rettungswege, Löschmittel und Brandmeldeanlage in Ordnung." },
      ],
      confidence: 95,
      related: ["brandschutzordnung-werk2", "feuerbeschau-2025"],
      followups: ["Wurde die Auflage aus der Feuerbeschau umgesetzt?", "Wer ist Brandschutzbeauftragter?"],
    },
  },
];

// Startvorschläge pro Modul (Frage-IDs). „wissen" zeigt die Highlights.
const MODULE_SUGGESTIONS = {
  wissen: ["reiserichtlinie", "materialkosten", "beleg-rechnung", "vertraege-verlaengerung", "vorstand-summary", "brandschutz"],
  finanzen: ["materialkosten", "beleg-rechnung"],
  audit: ["beleg-rechnung", "brandschutz"],
  hr: ["reiserichtlinie"],
  vertraege: ["vertraege-verlaengerung"],
  berichte: ["projekt-alpha", "vorstand-summary"],
  einstellungen: [],
};
