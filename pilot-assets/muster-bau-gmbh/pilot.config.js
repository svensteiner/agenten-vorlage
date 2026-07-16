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
      // Stand 2026-07-16: in den Struktur-Zwillingen (Rechnung/Rahmenvertrag), den
      // 3 Prosa-Zwillingen des Materialkosten-Szenarios (Q1-Bericht + 2 E-Mails) UND
      // den 4 Prosa-Zwillingen des Projekt-Beta-Szenarios (Status/Eskalation/Nachtrag/
      // Auftrag) bereits eingesetzt & verifiziert (procurement/cfo/legal/ceo → s.
      // README); die übrigen (hr/audit + 2 restliche Prosa-Belege des vorstand-
      // summary-Szenarios) folgen im gated Schritt 3.
      // ⚠ FRICTION (s. README): der Korpus trägt MEHRERE Projektleitungen ohne
      //   Config-Rolle — "Projektleitung Alpha" (Sabine Reinhardt → Sandra Bergmann)
      //   UND "Projektleitung Beta" (Markus Feldmann → Tobias Lindner). Eine EINZELNE
      //   `projectLead`-Rolle reicht nicht → Schritt 3: Liste `projectLeads` oder
      //   projekt-scoped Einträge (`projectLeadAlpha`/`projectLeadBeta`) ergänzen.
      ceo: "Andreas Moser",
      cfo: "Petra Hollmann",
      hr: "Miriam Baumgartner",
      procurement: "Jürgen Kessler",
      legal: "Dr. Stefan Reinhardt",
      audit: "Claudia Weiß",
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
