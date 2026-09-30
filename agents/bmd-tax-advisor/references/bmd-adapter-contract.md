# Vertrag für einen BMD-Adapter

Der Agent darf keine proprietäre BMD-API vermuten. Ein Adapter wird separat bereitgestellt,
versioniert und durch das Büro freigegeben. Standardmodus ist read-only bzw. Preview.

## Operationen

| Operation | Zweck | Standardfreigabe | Mindestnachweis |
|---|---|---|---|
| `read_client` | Mandant, Periode, Modul und Version feststellen | read-only | Mandanten-ID redigiert, Datenstand, Berechtigung |
| `read_documents` | Belege/Buchungsdaten für einen abgegrenzten Fall lesen | read-only | Quellen, Filter, Anzahl und Hash/Export-ID |
| `preview_import` | Import-/Buchungsvorschlag prüfen, ohne zu verbuchen | read-only | Format, Zeilen, Debet/Kredit, Steuerwerte, Duplikate |
| `export_report` | BMD-Auswertung oder Prüfbericht ablegen | read-only | Export-ID, Zeitraum, verwendete Parameter |
| `commit_posting` | echte Verbuchung oder Änderung ausführen | explizit autorisiert + Review | Autor, Freigabe-ID, Idempotency-Key, Vorher/Nachher |
| `submit_external` | FinanzOnline/sonstige Übermittlung auslösen | separate explizite Autorisierung | Ziel, Frist, Signatur-/Übermittlungsbeleg |

## Sicherheits- und Fehlerregeln

- Zugangsdaten, Tokens und vollständige Mandantenschlüssel bleiben im Secret Store bzw. in
  der BMD-Session; sie erscheinen nie in Prompt, Report oder Lernnotiz.
- Jede mutierende Operation braucht Mandant, Zeitraum, Datensatz-/Export-ID,
  Idempotency-Key, autorisierenden Benutzer und Audit-ID. Unklare oder wiederholte Wirkung
  führt zu `blocked`, nicht zu blindem Retry.
- Ein Adapter liefert strukturierte Beobachtungen: `status`, `summary`, `artifacts`,
  `evidence`, `next_actions`, plus `adapter_version` und `audit_id`.
- `preview_import` ist nicht `commit_posting`. Nach einem Commit muss der Adapter den
  tatsächlichen BMD-Zustand erneut lesen und die Abweichung dokumentieren.
- Fehlt ein Parameter oder weicht die Version vom lokalen Handbuch ab, darf der Agent nur
  einen konkreten Bedien-/Importplan erzeugen.
