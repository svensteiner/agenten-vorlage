# X Growth Agent

Der vorgesehene Startweg ist `Start-Marketing-Agent.ps1`. Er erzeugt vor jedem Start einen
kleinen Allowlist-Snapshot aus Status, Messdaten und den neuesten Reports. Der Agent erhaelt
keinen direkten Workspace-Zugriff auf den laufenden Marketingbot. Entwuerfe entstehen im
Snapshot unter `proposals/`; Live-X-Aktionen bleiben in der bestehenden Pipeline.

Dieser Agent ist die interaktive AgentKit-Bedienung fuer den bestehenden Marketingbot unter
`C:\Users\botrunner\projects\marketingbot`.

Aus dem AgentKit-Repository:

```powershell
& .\Start-Marketing-Agent.ps1
```

Der Browser startet mit diesem Agenten, dem Marketingbot-Workspace und Codex als echter
Modelllaufzeit. Der erste Auftrag ist als read-only Wachstumsanalyse vorbereitet und kann
vor dem Start bearbeitet werden. Datei- oder Testaktionen werden einzeln zur Freigabe
angezeigt. Der Launcher startet keinen zweiten Marketingbot-Scheduler und postet nichts.

Die Rollen und Skills basieren auf dem projektspezifischen Pack in
`marketingbot/project/`. Dieses Paket ist ein portabler Snapshot fuer AgentKit; die
Marketingbot-Laufzeit und deren Schutzgates bleiben autoritativ.

Fuer einen reinen Entwurfsauftrag kann der vorbereitete Text beispielsweise so ersetzt
werden; den belegbaren Quelltext direkt darunter einfuegen:

> Erstelle aus dem folgenden Quelltext hoechstens drei deutsche X-Posts mit je maximal
> 190 Zeichen. Beginne bei den Quellen statt bei alten Entwuerfen. Jeder Post braucht
> einen konkreten Einstieg und eine belegte Einsicht. Lege exakten Text, Zeichenzahl und
> Quellenzitate getrennt unter proposals/ ab. Lass die separate Verifier-Rolle die
> tatsaechlichen Entwuerfe pruefen und repariere begruendete Fehler. Dies ist ein
> Offline-Entwurfsauftrag; X-Wirkung ist unbekannt. Keine Veroeffentlichung.

Der begrenzte native Entwurfs-/Review-/Reparaturlauf ist nachgewiesen. Die breitere
Textqualitaetsabnahme ist noch offen; siehe `docs/AGENTIC-ACCEPTANCE.md` im Repository.
