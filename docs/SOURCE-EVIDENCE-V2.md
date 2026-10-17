# Quellenbelege: naechster Protokollschritt

**Entwurf, noch nicht implementiert oder abgenommen.** Die
[v15-Modellabnahme](evidence/execution-profiles-20261017/marketing-rich-v15-terminal.json)
liefert keinen freigegebenen Endtext. Ein Review scheitert konkret daran,
dass sein `source_quote` nicht exakt in der Beobachtung vorkommt. Die beiden
`repair_failed`-Faelle haben damit noch keine nachgewiesene Detailursache.

## Entscheidung

Der Host soll genaue Quellfragmente bereitstellen; das Modell soll deren
numerische IDs auswaehlen. Ein strikter lokaler Adapter setzt die IDs wieder
in die originalen Quellstrings ein. Erst danach entscheidet der unveraenderte
`_parse_review` ueber die bisherige Review-Antwort.

Ein Enum aus ganzen Quellzitaten ist dafuer ungeeignet: Anthropic dokumentiert
Abweichungen bei der Gross-/Kleinschreibung von String-Enum-Werten. Ausserdem
koennen Schemas zwischengespeichert werden; Quellinhalt gehoert deshalb in
Promptdaten, nicht in Schema-Enums. `minLength` und `maxLength` werden vom
rohen Structured-Output-Schema nicht unterstuetzt. Lokale Zeichenpruefungen
bleiben erforderlich. [Offizielle Einschraenkungen](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

## Unveraenderliche Anforderungen

- Der Host erstellt pro Qualifikation einen eigenen Belegsatz mit numerischer
  Nonce und numerischen Fragment-IDs. Strikte Integerpruefung verwirft auch
  Booleans und Floats. Alte Nonces und unbekannte IDs sind ungueltig.
- Fragmente sind exakte zusammenhaengende Teilstrings. Ihre geordnete
  Rekonstruktion muss die vollstaendige Eingabe einschliesslich Unicode und
  Begrenzungen erhalten. Der Host klassifiziert sie nicht als wahre Fakten.
- Eine atomare Entwurfsaussage verweist auf genau einen angebotenen Beleg.
  Der Adapter akzeptiert nur die geschlossene v2-Antwort, ohne alte
  `source_quote`-Felder oder gemischte Protokolle, und erweitert keine Zitate.
- Eine explizite Protokollversion trennt alte Callbacks von v2. Der neue
  News-Pfad waehlt v2 ausdruecklich; es gibt keinen v2-zu-v1-Fallback.
- Schema und Prompt muessen dieselbe Version beschreiben. Quelltext bleibt
  untrusted Daten. Beide bestehenden typisierten Providerpfade, Anthropic
  und OpenRouter, brauchen exakte Payloadtests; allgemeine Freiform-Aufrufe
  bleiben unveraendert.
- Anzahl der Modellaufrufe, derselbe TaskBudget-Kontext, physische Call-Limits,
  Inhaltspruefungen und Regeln fuer unbekannte Ausgaenge bleiben erhalten.
  Groesse und lokale Reservierung werden vor Dispatch geprueft; kein
  Abschneiden von Belegen oder schemafreier Ersatz bei Ueberschreitung.

IDs verhindern keine falsche Belegwahl. Ein vorhandener Quellstring kann
die zugeordnete Aussage weiterhin nicht tragen. Semantische Pruefung,
Kontrollerhalt, Unsicherheit, Zeichenlimit und unabhaengige Inhaltsabnahme
bleiben eigene Anforderungen.

## Erforderliche Nachweise

Regressionen muessen exakte Expansion und unveraenderten Originalparser,
falsche Nonces/IDs/Typen, gemischte Felder, doppelte JSON-Schluessel,
unveraenderten Reparaturablauf, verlustlose lange Unicode-Eingaben,
Uebergroesse vor HTTP und unveraenderte andere Provideraufgaben pruefen.
Der Adapter darf einen gueltigen Beleg nicht selbst freigeben, sondern muss
weiter den Originalparser aufrufen. Dieser Parser prueft die Antwortstruktur;
er erkennt nicht jede semantisch unpassende Zuordnung. Tests muessen sowohl
die erhaltene Ablehnung als auch ein strukturell gueltiges Gegenbeispiel mit
unpassendem Beleg dokumentieren, statt semantische Sicherheit vorzutäuschen.
Danach sind Gesamttest, separates Review und ein vorab
festgelegter echter Modelllauf notwendig. Vorher gibt es keine
Produktionsfreigabe oder Behauptung besserer Posts.
