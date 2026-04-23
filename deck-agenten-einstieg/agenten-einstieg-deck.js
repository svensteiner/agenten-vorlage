const path = require("path");
const pptxgen = require("pptxgenjs");
const {
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./assets/pptxgenjs_helpers/layout");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Codex";
pptx.company = "agenten-vorlage";
pptx.subject = "Einstieg in eine wiederverwendbare Agenten-Vorlage";
pptx.title = "Wie ein Agent entsteht";
pptx.lang = "de-DE";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "de-DE",
};

const C = {
  bg: "0F1115",
  panel: "171A21",
  panel2: "1D2230",
  line: "2A3242",
  text: "F4F7FB",
  muted: "B2BAC8",
  teal: "39D0C5",
  teal2: "22A7F0",
  coral: "FF7A59",
  gold: "F4C95D",
  green: "79D27F",
};

function addBg(slide) {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 7.5,
    fill: { color: C.bg },
    line: { color: C.bg },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: 13.333,
    h: 0.16,
    fill: { color: C.teal },
    line: { color: C.teal },
  });
}

function addTitle(slide, kicker, title, subtitle) {
  slide.addText(kicker.toUpperCase(), {
    x: 0.6,
    y: 0.34,
    w: 2.8,
    h: 0.18,
    fontFace: "Aptos",
    fontSize: 10,
    bold: true,
    color: C.teal,
    charSpace: 1.1,
    margin: 0,
  });
  slide.addText(title, {
    x: 0.6,
    y: 0.56,
    w: 11.9,
    h: 0.42,
    fontFace: "Aptos Display",
    fontSize: 24,
    bold: true,
    color: C.text,
    margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.6,
      y: 1.03,
      w: 11.9,
      h: 0.24,
      fontFace: "Aptos",
      fontSize: 10.5,
      color: C.muted,
      margin: 0,
    });
  }
}

function addFooter(slide, text) {
  slide.addText(text, {
    x: 0.6,
    y: 7.03,
    w: 12.1,
    h: 0.18,
    fontFace: "Aptos",
    fontSize: 8.5,
    color: C.muted,
    margin: 0,
    align: "right",
  });
}

function addCard(slide, x, y, w, h, title, body, accent, titleSize = 13.5, bodySize = 10.3) {
  slide.addShape(pptx.ShapeType.rect, {
    x: x + 0.18,
    y: y + 0.18,
    w: 0.11,
    h: Math.max(0.34, Math.min(0.46, h - 0.28)),
    fill: { color: accent },
    line: { color: accent },
  });
  slide.addText(
    [
      { text: `${title}\n`, options: { bold: true, fontSize: titleSize, color: C.text } },
      { text: body, options: { fontSize: bodySize, color: C.muted } },
    ],
    {
      x,
      y,
      w,
      h,
      fontFace: "Aptos",
      fill: { color: C.panel2 },
      line: { color: C.line, pt: 1 },
      rectRadius: 0.08,
      margin: 0.14,
      valign: "top",
    }
  );
}

function addPill(slide, x, y, w, text, fill) {
  slide.addText(text, {
    x,
    y,
    w,
    h: 0.42,
    fontFace: "Aptos",
    fontSize: 10.5,
    bold: true,
    color: "FFFFFF",
    align: "center",
    valign: "mid",
    margin: 0,
    fill: { color: fill },
    line: { color: fill },
    rectRadius: 0.08,
  });
}

function addArrow(slide, x1, y1, x2, y2, color) {
  slide.addShape(pptx.ShapeType.line, {
    x: x1,
    y: y1,
    w: x2 - x1,
    h: y2 - y1,
    line: { color, pt: 1.5, endArrowType: "triangle" },
  });
}

// Slide 1
{
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(
    slide,
    "Überblick",
    "Wie entsteht ein Agent?",
    "Wenige Fragen, klares Manifest, sauberer Core. So wird aus einer Idee eine Vorlage, die man wiederverwenden kann."
  );

  addCard(
    slide,
    0.72,
    1.72,
    2.9,
    2.0,
    "1. Fragen",
    "Der Einstieg ist einfach: Was soll der Agent tun? Für wen ist er gedacht? Welche Tools braucht er?",
    C.teal
  );
  addCard(
    slide,
    3.82,
    1.72,
    2.9,
    2.0,
    "2. Manifest",
    "Aus den Antworten wird eine strukturierte Datei. Der Agent kann sie später direkt lesen.",
    C.coral
  );
  addCard(
    slide,
    6.92,
    1.72,
    2.9,
    2.0,
    "3. Core",
    "Context, Planner, Governance und Verifier arbeiten die Aufgabe zuverlässig ab.",
    C.gold
  );
  addCard(
    slide,
    10.02,
    1.72,
    2.58,
    2.0,
    "4. Ergebnis",
    "Tools und Subagenten liefern das fertige Resultat.",
    C.green
  );

  addArrow(slide, 3.63, 2.72, 3.76, 2.72, C.line);
  addArrow(slide, 6.73, 2.72, 6.86, 2.72, C.line);
  addArrow(slide, 9.83, 2.72, 9.96, 2.72, C.line);

  addCard(
    slide,
    0.72,
    4.14,
    12.02,
    1.86,
    "Warum das wichtig ist",
    "Der Nutzer soll nicht zuerst ein Handbuch verstehen müssen. Die Vorlage fragt einfach, erzeugt die Grundstruktur und bleibt trotzdem stark genug für echte Automationen.",
    C.teal2,
    14,
    11
  );
  addPill(slide, 1.02, 6.18, 2.3, "einfach starten", C.teal);
  addPill(slide, 3.52, 6.18, 2.65, "sauber strukturieren", C.coral);
  addPill(slide, 6.35, 6.18, 2.55, "sicher ausführen", C.gold);
  addPill(slide, 9.08, 6.18, 2.8, "leicht wiederverwenden", C.green);
  addFooter(slide, "Agenten-Vorlage: Einstieg, Struktur und Umsetzung");
}

// Slide 2
{
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(
    slide,
    "Schritt 1",
    "Mit einfachen Fragen anfangen",
    "Für Anfänger zählt: kurze Fragen, klare Sprache, gute Defaults. Die Vorlage führt den Einstieg, ohne ihn schwer zu machen."
  );

  addCard(
    slide,
    0.72,
    1.72,
    4.05,
    1.0,
    "Was soll der Agent tun?",
    "Die Aufgabe in einem Satz. Kein Fachjargon.",
    C.teal
  );
  addCard(
    slide,
    0.72,
    2.9,
    4.05,
    1.0,
    "Für wen ist er gedacht?",
    "Der Kontext hilft bei Ton, Sprache und Regeln.",
    C.coral
  );
  addCard(
    slide,
    0.72,
    4.08,
    4.05,
    1.0,
    "Welche Tools braucht er?",
    "Zum Beispiel Excel, E-Mail, Web oder APIs.",
    C.gold
  );

  addCard(
    slide,
    5.08,
    1.72,
    7.66,
    3.36,
    "Warum dieser Schritt zählt",
    "Der Einstieg darf sich leicht anfühlen. Wenn die ersten Fragen einfach sind, kann auch ein Anfänger die Vorlage nutzen.\n\nDie Qualität bleibt trotzdem hoch, weil sinnvolle Vorgaben den Rest übernehmen.",
    C.green,
    15,
    11
  );
  addCard(
    slide,
    5.08,
    5.34,
    7.66,
    1.14,
    "Ergebnis",
    "Aus wenigen Antworten entsteht direkt ein brauchbares Projektpaket.",
    C.teal2,
    13.5,
    10.8
  );

  addFooter(slide, "Schritt 1: Einstieg so einfach wie möglich");
}

// Slide 3
{
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(
    slide,
    "Schritt 2",
    "Das Manifest macht aus Antworten ein System",
    "Die Antworten werden in klare Dateien übersetzt. So kann der Agent sie wirklich lesen und die Vorlage später wiederverwenden."
  );

  addCard(
    slide,
    0.72,
    1.72,
    3.9,
    3.9,
    "Manifest",
    "Projektname\nZiel\nFreigaben\nTools\nWorkflow\nMemory-Regeln",
    C.teal
  );
  addCard(
    slide,
    4.82,
    1.72,
    3.9,
    3.9,
    "SOUL.md",
    "Rolle\nTon\nGrenzen\nQualitätsmaß\nWas wichtig ist",
    C.coral
  );
  addCard(
    slide,
    8.92,
    1.72,
    3.68,
    3.9,
    "Warum das hilft",
    "Der Planner bekommt Fakten statt Vermutungen.\n\nRegeln liegen sichtbar in Dateien statt versteckt im Kopf.\n\nNeue Projekte lassen sich viel schneller kopieren.",
    C.gold,
    14,
    10.8
  );
  addFooter(slide, "Schritt 2: Antworten werden zu Manifest und Projektsprache");
}

// Slide 4
{
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(
    slide,
    "Schritt 3",
    "Der Core arbeitet die Aufgabe ab",
    "Der Kern bleibt gleich, egal ob Excel, E-Mail oder andere Automationen dahinterstecken."
  );

  addPill(slide, 0.9, 1.9, 1.95, "Context", C.teal);
  addPill(slide, 3.08, 1.9, 1.95, "Planner", C.coral);
  addPill(slide, 5.26, 1.9, 1.95, "Governance", C.gold);
  addPill(slide, 7.44, 1.9, 1.95, "Dispatcher", C.teal2);
  addPill(slide, 9.62, 1.9, 1.95, "Verifier", C.green);
  addPill(slide, 11.8, 1.9, 0.63, "Ende", C.coral);

  addArrow(slide, 2.86, 2.13, 3.02, 2.13, C.line);
  addArrow(slide, 5.04, 2.13, 5.2, 2.13, C.line);
  addArrow(slide, 7.22, 2.13, 7.38, 2.13, C.line);
  addArrow(slide, 9.4, 2.13, 9.56, 2.13, C.line);
  addArrow(slide, 11.58, 2.13, 11.74, 2.13, C.line);

  addCard(
    slide,
    0.72,
    2.78,
    3.95,
    2.5,
    "Warum dieser Ablauf?",
    "Context: Aufgabe und Regeln zusammenbringen.\nPlanner: den besten Weg wählen.\nGovernance: nur sichere Aktionen erlauben.",
    C.teal2
  );
  addCard(
    slide,
    4.88,
    2.78,
    3.95,
    2.5,
    "Was danach passiert",
    "Dispatcher: Tool oder Subagent ausführen.\nVerifier: Ergebnis prüfen.\nDann erst geht es weiter.",
    C.green
  );
  addCard(
    slide,
    9.04,
    2.78,
    3.6,
    2.5,
    "Warum das stark ist",
    "Weniger Fehler.\nWeniger Korrekturen.\nMehr Vertrauen.",
    C.coral
  );
  addFooter(slide, "Schritt 3: der Core führt aus und prüft");
}

// Slide 5
{
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(
    slide,
    "Fazit",
    "Die Vorlage soll einfach sein und trotzdem stark bleiben",
    "Der beste Einstieg ist der, den man sofort versteht. Danach sorgt die Struktur dafür, dass der Agent professionell bleibt."
  );

  addCard(
    slide,
    0.72,
    1.78,
    5.95,
    3.78,
    "Der einfache Weg",
    "1. Wenige Fragen beantworten\n2. Manifest und SOUL erzeugen\n3. Core und Subagenten nutzen\n4. Ergebnis prüfen und speichern",
    C.teal,
    14,
    11
  );
  addCard(
    slide,
    6.9,
    1.78,
    5.7,
    3.78,
    "Warum das gut ist",
    "Für Anfänger leicht verständlich\nFür Teams schnell wiederholbar\nFür Kunden sauber anpassbar\nFür spätere Erweiterungen offen",
    C.coral,
    14,
    11
  );
  addCard(
    slide,
    0.72,
    5.84,
    11.88,
    0.9,
    "Merksatz",
    "Nicht ein einzelner Bot, sondern ein kleines Baukastensystem für Automationen.",
    C.gold,
    14,
    10.8
  );
  addFooter(slide, "Fazit: einfache Anwendung, aber starke Struktur");
}

for (const slide of pptx._slides) {
  warnIfSlideHasOverlaps(slide, pptx, { muteContainment: true });
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

async function main() {
  const out = path.join(__dirname, "agenten-einstieg.pptx");
  await pptx.writeFile({ fileName: out });
  console.log(`Wrote ${out}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
