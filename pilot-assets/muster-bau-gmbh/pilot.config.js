/*
 * pilot.config.js — Pilot-Umbranding (Schicht A / Chrome) für den Probelauf-Kunden
 * "Muster Bau GmbH". EIN Pilot = EINE solche Datei.
 *
 * ALLE Werte sind 100 % SYNTHETISCH — kein echter Kundenname, kein Logo-Bild
 * (nur ein Unicode-Glyph). Diese Datei ist der ausgeführte Schritt "Schicht A
 * schreiben" aus PILOT_CONFIG_SPEC.md §4 für den fiktiven End-to-End-Probelauf.
 *
 * ⚠ FREEZE-GRENZE: Diese Datei liegt bewusst in pilot-assets/ und ist NICHT in
 *   prototype/ verdrahtet. Das Wiring (Script-Tag + COMPANY-Guard + applyPilotChrome())
 *   berührt prototype/ und wird erst NACH Gate B→C ausgeführt (Feature-Freeze in
 *   Phase B). Bis dahin ist dies ein verifizierter, aufnahmebereiter Ausgangspunkt.
 *
 * Verwandt: ../../PILOT_CONFIG_SPEC.md (Schema+Wiring) · ../../SCENARIO_LIBRARY.md
 *   (die 3 Szenarien) · ../../SYNTHETIC_DATA_PIPELINE.md (Schicht B / Korpus) ·
 *   ./README.md (Schritte 1+2: synthetischer Zwilling bereits erzeugt).
 */
window.PILOT_CONFIG = {
  active: true, // false → unveränderte Meridian-Demo (Regressionsschutz fürs Video)

  company: {
    name: "Muster Bau GmbH", // ersetzt COMPANY.name überall in der Shell
    tagline: "Hoch- & Tiefbau · Region Süd",
    logoGlyph: "▲", // 1 Zeichen; ersetzt ✦ im Kopf + Onboarding
    accent: "#1f6feb", // optional: CSS --accent; weglassen = Marken-Indigo behalten
    facts: [
      // 3–4 synthetische Kennzahlen für die Firmenkarte
      { label: "Gegründet", value: "1998" },
      { label: "Mitarbeitende", value: "180" },
      { label: "Standorte", value: "Augsburg · Werkhof Kempten" },
      { label: "Umsatz 2025", value: "48 Mio. €" },
    ],
    people: {
      // Synthetische Namen — ersetzen die Meridian-Personen 1:1 im synth. Korpus.
      // Stand 2026-07-21 (Korpus 12/12 vollständig; Voll-Korpus-Kohärenz-Audit):
      //   • Eingesetzt & in ≥1 Zwilling verifiziert: ceo(Moser) · cfo(Hollmann) ·
      //     procurement(Kessler) · legal(Reinhardt). (0 Meridian-Leak über alle 12.)
      //   • ⚠ hr(Baumgartner) & audit(Weiß) erscheinen in 0 Zwillingen — KORREKT &
      //     erwartet: die 3 gewählten Pilot-Szenarien (materialkosten · projekt-beta ·
      //     vorstand-summary) referenzieren KEINE HR-/Audit-Persona. Das sind daher
      //     UNGENUTZTE Korpus-Mapping-Einträge (harmlos: applyPilotChrome nutzt `people`
      //     nur fürs Korpus-Ersetzen, nicht für die Firmenkarte). Für Schritt 3: NICHT
      //     nach HR-/Audit-Belegen suchen — es gibt keine. Bei anderer Szenario-Wahl
      //     (z. B. datenschutz-audit / onboarding) würden sie relevant.
      //   (Frühere Notiz „hr/audit + 2 restliche vorstand-Belege folgen in Schritt 3"
      //    war überholt: die vorstand-Zwillinge sind seit 2026-07-17 gestaged.)
      // ✅ FRICTION GELÖST (2026-07-19): der Korpus trägt MEHRERE Projektleitungen,
      //   für die eine EINZELNE `projectLead`-Rolle nicht reicht. Statt einer flachen
      //   Rolle jetzt projekt-scoped in `projectLeads` (s.u.) — deckt beide Projekte
      //   und den Alpha-Doppel-Lead faithful ab. Die einzelnen Rollen unten bleiben
      //   für die Nicht-Projekt-Personen (CEO/CFO/HR/Einkauf/Recht/Audit). Wiring
      //   (Konsum durch applyPilotChrome/Korpus-Mapping) berührt prototype/ → Schritt 3.
      ceo: "Andreas Moser",
      cfo: "Petra Hollmann",
      hr: "Miriam Baumgartner",
      procurement: "Jürgen Kessler",
      legal: "Dr. Stefan Reinhardt", // ≠ projectLead Reinhardt: bewusst getrennt (Kollision vermieden)
      audit: "Claudia Weiß",
    },

    // Projekt-scoped Projektleitungen (Schritt-3-Empfehlung, jetzt umgesetzt).
    // Quelle nennt für Alpha ZWEI Namen (Meridian-Inkonsistenz, faithful gemappt,
    // nicht eingeebnet); Beta einen. Synth. Namen bereits in den Zwillingen gesetzt
    // & verifiziert (0 Meridian-Leak): s. projekt-alpha-status / projekt-beta-status /
    // eskalation-beta / email-weiterleitung-materialbudget.
    projectLeads: {
      alpha: ["Sandra Bergmann", "Nadine Falk"], // Sabine Reinhardt / Ing. Petra Lang
      beta: ["Tobias Lindner"], // Markus Feldmann
    },
  },

  industry: "bau", // steuert die Szenario-Vorauswahl

  // GENAU 3 Schmerz-Szenarien (verifiziert gegen data.js / SCENARIO_LIBRARY.md
  // "Fertige 3er-Auswahlen" → Zeile "Bau / Anlagenbau"). Der Money-Shot
  // `agent-dazubuchen` wird vom Umbranding NICHT angefasst und bleibt Demo-Finale.
  scenarios: [
    "materialkosten", // KOSTEN — passt zur Bau-Controlling-Mappe (Schritte 1+2)
    "projekt-beta", // PROJEKTE — Terminrisiko, ehrlich statt beschönigt
    "vorstand-summary", // MONATSABSCHLUSS — Vorstands-Kurzfassung
  ],

  corpus: "muster-bau", // Zeiger auf den synth. Korpus (Schicht B); s. ./README.md
};
