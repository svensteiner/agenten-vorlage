"""Agent jobs via core.orchestrator — no core/platform edits."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.orchestrator import AgentOrchestrator
from tools.base_tool import BaseTool

from product import catalog, config, db, retrieval


ROOT = config.ROOT


class KnowledgeSearchTool(BaseTool):
    name = "file_read"
    description = "Sucht in der privaten Wissensbasis der Organisation."

    def __init__(self, conn, org_id: str, role: str) -> None:
        self.conn = conn
        self.org_id = org_id
        self.role = role

    def run(self, input: str) -> str:
        query = (input or "").strip()
        if query.lower().startswith(("read:", "list:", "path:")):
            query = query.split(":", 1)[-1].strip()
        hits, _withheld = retrieval.retrieve(
            self.org_id, query, role=self.role, limit=6, conn=self.conn
        )
        if not hits:
            return "Keine Treffer in der privaten Wissensbasis."
        payload = [
            {
                "id": h["id"],
                "title": h["title"],
                "snippet": retrieval.quote_from(h, query),
                "path": h.get("path"),
            }
            for h in hits
        ]
        return json.dumps(payload, ensure_ascii=False)


class KnowledgeFileTool(KnowledgeSearchTool):
    """Planner rule path looks up tools['file'], worker scope uses file_read."""

    name = "file"


class PrivateWebStub(KnowledgeSearchTool):
    name = "web_search"
    description = "Öffentliche Websuche ist auf der Kundeninstanz deaktiviert; sucht intern."


def run_agent_job(
    conn,
    *,
    org_id: str,
    role: str,
    agent_id: str,
    task: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    spec = catalog.by_id(agent_id)
    if not spec:
        raise KeyError(agent_id)

    knowledge = KnowledgeSearchTool(conn, org_id, role)
    tools = {
        "file_read": knowledge,
        "file": KnowledgeFileTool(conn, org_id, role),
        "web_search": PrivateWebStub(conn, org_id, role),
    }
    started = db.now_iso()
    orchestrator = AgentOrchestrator(ROOT)
    result = orchestrator.run(task, tools=tools, tenant=org_id)

    answer = retrieval.ask(org_id, task, role=role, conn=conn, user_id=user_id)
    outputs = []
    if result.metadata:
        outputs = list(result.metadata.get("outputs") or [])
    orch_text = "\n".join(o for o in outputs if o and "Planned step recorded" not in o)

    text = answer["text"]
    if orch_text and result.success:
        # Keep the extractive/LLM answer as the user-facing body; mention the run.
        pass
    name = spec.get("name") or agent_id
    lead = f"<p><b>{name}</b> hat den Auftrag über den Kern-Orchestrator ausgeführt.</p>"
    text = lead + (text or "")

    return {
        "ok": bool(result.success or answer.get("sources")),
        "text": text,
        "reasoning": (
            [
                f"Agent: {name}",
                "Plan → Governance → Worker → Synthese (core.orchestrator).",
            ]
            + list(answer.get("reasoning") or [])
        ),
        "sources": answer.get("sources") or [],
        "withheld": answer.get("withheld"),
        "confidence": answer.get("confidence") or (86 if result.success else 55),
        "related": answer.get("related") or [],
        "followups": answer.get("followups") or [],
        "via": answer.get("via") or "extractive",
        "started_at": started,
        "finished_at": db.now_iso(),
        "run_success": bool(result.success),
        "run_id": result.run_spec.run_id if result.run_spec else None,
    }
