"""Handoff — Cross-agent routing mit Allowlist und Schema-Validierung.

Ein Handoff übergibt die Kontrolle von einem Agenten an einen anderen.
Der Agent signalisiert einen Handoff durch einen strukturierten Block
in seinem Output:

    <<HANDOFF>>
    {
        "target": "reader",
        "task": "Analysiere Datei reports/q1.csv",
        "context": {"focus": "umsatz"}
    }
    <<END_HANDOFF>>

Oder alternativ im Plan-Dict via "handoff"-Key:

    {
        "understood": "...",
        "plan": [...],
        "handoff": {"target": "writer", "task": "Schreibe Report"}
    }

HandoffRouter:
1. Extrahiert Handoff-Request aus Text oder Plan-Dict
2. Validiert Target gegen Allowlist
3. Prüft Payload-Größe und Pflichtfelder
4. Gibt validierten Request zurück — Ausführung obliegt dem Aufrufer

Verwendung:
    from handoff import HandoffRouter, HandoffRequest

    router = HandoffRouter(allowlist=["reader", "writer"], max_payload_chars=2000)

    req = router.extract(agent_output_text)
    if req:
        ok, reason = router.validate(req)
        if ok:
            # execute handoff ...
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("handoff")

_HANDOFF_PATTERN = re.compile(
    r"<<HANDOFF>>(.*?)<<END_HANDOFF>>",
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class HandoffRequest:
    target: str
    task: str
    context: dict = field(default_factory=dict)

    def payload_size(self) -> int:
        return len(self.task) + len(json.dumps(self.context, ensure_ascii=False))


class HandoffRouter:
    """Validiert und routet Handoff-Requests zwischen Agenten."""

    def __init__(self, allowlist: list[str], max_payload_chars: int = 2000) -> None:
        self._allowlist: frozenset[str] = frozenset(allowlist)
        self._max_payload = max_payload_chars

    # ── Extraktion ────────────────────────────────────────────────────────

    def extract(self, text: str) -> Optional[HandoffRequest]:
        """Sucht <<HANDOFF>>...<<END_HANDOFF>> Block im Text.

        Returns HandoffRequest oder None wenn kein Block gefunden.
        """
        match = _HANDOFF_PATTERN.search(text)
        if not match:
            return None
        raw = match.group(1).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Handoff: ungültiges JSON — %s", exc)
            return None
        return self._from_dict(payload)

    def extract_from_plan(self, plan: dict) -> Optional[HandoffRequest]:
        """Liest Handoff aus plan["handoff"] falls vorhanden."""
        hf = plan.get("handoff")
        if not hf:
            return None
        if isinstance(hf, dict):
            return self._from_dict(hf)
        return None

    def _from_dict(self, data: dict) -> Optional[HandoffRequest]:
        target = data.get("target", "").strip()
        task = data.get("task", "").strip()
        if not target:
            logger.warning("Handoff: 'target' fehlt")
            return None
        if not task:
            logger.warning("Handoff: 'task' fehlt")
            return None
        return HandoffRequest(
            target=target,
            task=task,
            context=data.get("context", {}),
        )

    # ── Validierung ───────────────────────────────────────────────────────

    def validate(self, request: HandoffRequest) -> tuple[bool, str]:
        """Prüft ob der Handoff-Request erlaubt ist.

        Returns:
            (True, "")          wenn gültig
            (False, Grund)      wenn abgelehnt
        """
        if request.target not in self._allowlist:
            return False, (
                f"Handoff-Target '{request.target}' nicht in Allowlist. "
                f"Erlaubt: {sorted(self._allowlist)}"
            )
        size = request.payload_size()
        if size > self._max_payload:
            return False, (
                f"Handoff-Payload zu groß: {size} Zeichen "
                f"(Maximum: {self._max_payload})"
            )
        return True, ""

    @property
    def allowlist(self) -> list[str]:
        return sorted(self._allowlist)


def load_router(manifest: Optional[dict] = None) -> HandoffRouter:
    """Erstellt HandoffRouter aus manifest oder mit leerer Allowlist."""
    if not manifest:
        return HandoffRouter(allowlist=[])
    hf_cfg = manifest.get("handoffs", {})
    return HandoffRouter(
        allowlist=hf_cfg.get("allowlist", []),
        max_payload_chars=hf_cfg.get("max_payload_chars", 2000),
    )
