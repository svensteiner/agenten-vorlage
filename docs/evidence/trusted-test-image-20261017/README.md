# Vertrauenswuerdiges Testimage: lokaler Build und Importpruefung

Das vom Host vorgegebene Linux-amd64/Python-3.12-Image wurde erfolgreich gebaut.
Basis: das im Dockerfile per Digest gebundene offizielle Python-Image.
15 zuvor heruntergeladene Wheels wurden jeweils gegen den SHA-256-Wert der
zugehoerigen [PyPI-Metadaten](https://pypi.org/) geprueft; jede genaue
Metadatenadresse steht im Inventar. Die separate Codepruefung hat diese
lokalen Wheelhashes und den Lockhash unabhaengig nachgerechnet.

Der Build installiert ausschliesslich lokale Wheels mit --no-index und
--require-hashes bei Docker --network=none. Der Lockhash ist als Image-Label
gespeichert. Das fertige Image wird ueber seine unveraenderliche SHA-256-ID
angesprochen, nicht ueber den waehrend des Builds verwendeten Tag.
Buildlog, Dockerfile, Lock, Inventar und Image-ID sind beigefuegt.

Eine echte Containerpruefung mit Netzwerk aus, read-only Root, UID 65534,
cap-drop ALL, no-new-privileges und Ressourcenlimits bestaetigt die installierten
Versionen: pytest 9.0.3, PyYAML 6.0.3, jsonschema 4.26.0, pypdf 6.19.0,
defusedxml 0.7.1. Plugin-Autoload und Bytecode sind im Image deaktiviert.

**Grenzen:** Das Image ist nur lokal gebaut, nicht in eine Registry publiziert.
Die binaeren Wheels sind nicht in diesem Git-Beleg enthalten. Zum Nachbauen
muessen die genau inventarisierten Dateien beschafft und erneut gegen Lock und
Inventar geprueft werden. Kein Projekt-/Modellauftrag lief in dieser
Importpruefung. Diese Belege allein beweisen weder ein fertiges Agentenwerkzeug
noch einen bestandenen autonomen Coding-Auftrag oder Produktionsreife.
