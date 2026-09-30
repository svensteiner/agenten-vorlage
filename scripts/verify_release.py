"""Offline release gate for the portable AgentKit template."""

from __future__ import annotations

import json
import argparse
import base64
import io
import zipfile
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentkit.backends import DemoBackend  # noqa: E402
from agentkit.catalog import Catalog  # noqa: E402
from agentkit.contracts import read_json  # noqa: E402
from agentkit.engine import Engine  # noqa: E402
from agentkit.scaffold import create  # noqa: E402
from cockpit.conversations import Conversations  # noqa: E402
from cockpit.server import JobManager  # noqa: E402


def check(name: str, operation) -> dict:
    try:
        value = operation()
        result = {"name": name, "ok": True}
        if value is not None:
            result["result"] = value
        return result
    except Exception as exc:
        return {"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows-ocr", action="store_true", help="Require a real local Windows OCR attachment/recovery check.")
    options = parser.parse_args()
    profiles = read_json(ROOT / "agentkit" / "library" / "profiles.json")
    checks: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="agentkit-release-") as temporary:
        temporary_root = Path(temporary)
        for profile in profiles:
            checks.append(check(
                f"profile:{profile}",
                lambda profile=profile: Catalog(create(
                    temporary_root / profile, profile, f"verify-{profile}", "release-check"
                )).config["profile"],
            ))

        def run_demo() -> dict:
            agent = create(temporary_root / "demo-developer", "developer", "demo-developer", "release-check")
            result = Engine(agent, agent / "workspace", DemoBackend()).run(
                "Run the deterministic offline acceptance demo."
            )
            if result.get("status") != "completed":
                raise RuntimeError(f"demo ended with status {result.get('status')!r}")
            return {"status": result["status"]}

        checks.append(check("offline-demo:developer", run_demo))

        def run_conversation_demo() -> dict:
            app_root = temporary_root / "conversation-app"
            agent = create(app_root / "agents" / "dialog", "developer", "dialog", "release-check")
            manager = JobManager(app_root)
            conversations = Conversations(manager)
            conversation = conversations.create({
                "request_id": "1" * 32, "agent": str(agent),
                "workspace": str(agent / "workspace"), "backend": "demo", "title": "Release dialog",
            })
            for number, content in ((2, "Remember RELEASE-DIALOG-OK"), (3, "Use the earlier context")):
                request_id = str(number) * 32
                conversations.send(conversation["id"], {"request_id": request_id, "content": content})
                job = manager.get(request_id)
                job.thread.join(15)
                if job.status != "completed":
                    raise RuntimeError(f"conversation message ended with {job.status}")
            restored = Conversations(JobManager(app_root)).get(conversation["id"])
            if len(restored["messages"]) != 4 or "RELEASE-DIALOG-OK" not in job.result["task"]:
                raise RuntimeError("Conversation history/context did not survive")
            return {"messages": 4, "restart_restored": True, "backend": "demo"}

        checks.append(check("offline-conversation:two-turn-recovery", run_conversation_demo))

        def run_approval_demo() -> dict:
            agent = create(temporary_root / "approval-demo", "developer", "approval-demo", "release-check")
            workspace = agent / "workspace"
            state = Engine(agent, workspace, DemoBackend(), require_approvals=True).run("Verify exact action approvals")
            if state["status"] != "awaiting_approval" or (workspace / "demo-result.md").exists():
                raise RuntimeError("Write was not paused before dispatch")
            count = 0
            while state["status"] == "awaiting_approval" and count < 3:
                state = Engine(agent, workspace, DemoBackend()).run(
                    "", run_dir=agent / ".runs" / state["run_id"],
                    approval_id=state["pending_approval"]["id"], approval_decision="approve",
                )
                count += 1
            if state["status"] != "completed" or count != 2 or not state["reviewed"]:
                raise RuntimeError("Approved demo did not preserve per-write gates and review")
            return {"approvals": count, "status": state["status"], "backend": "demo"}

        checks.append(check("offline-approvals:exact-action-recovery", run_approval_demo))

        def run_instruction_edit_demo() -> dict:
            app_root = temporary_root / "instruction-app"
            agent = create(app_root / "agents" / "editor", "developer", "editor", "release-check")
            manager = JobManager(app_root)
            initial = manager.get_instructions(str(agent))
            old = manager.update_instructions({"agent": str(agent), "revision": initial["revision"],
                                               "text": initial["text"] + "\nRELEASE-INSTRUCTIONS-OLD\n"})
            payload = {"agent": str(agent), "workspace": str(agent / "workspace"),
                       "backend": "demo", "task": "Verify assistant revision", "require_approvals": True}
            job = manager.start(payload)
            job.thread.join(15)
            if job.thread.is_alive() or job.status != "awaiting_approval":
                raise RuntimeError("Instruction check did not pause before the write")
            frozen = job.result["core_snapshot"]
            proposal = job.result["pending_approval"]
            manager.update_instructions({"agent": str(agent), "revision": old["revision"],
                                         "text": initial["text"] + "\nRELEASE-INSTRUCTIONS-NEW\n"})
            manager = JobManager(app_root)
            job = manager.get(job.job_id)
            if job.result["pending_approval"] != proposal:
                raise RuntimeError("Editing instructions changed a pending action")
            count = 0
            while job.status == "awaiting_approval" and count < 3:
                job = manager.approval(job.job_id, job.result["pending_approval"]["id"], "approve")
                job.thread.join(15)
                if job.thread.is_alive():
                    raise RuntimeError("Instruction check worker did not stop")
                count += 1
            if job.status != "completed" or count != 2 or not job.result["reviewed"]:
                raise RuntimeError("Original instruction revision did not complete its approvals/review")
            if job.result["core_snapshot"] != frozen or "RELEASE-INSTRUCTIONS-OLD" not in frozen:
                raise RuntimeError("Existing task lost its original instructions")
            next_job = manager.start({**payload, "task": "Use the edited assistant", "require_approvals": False})
            next_job.thread.join(15)
            if (next_job.thread.is_alive() or next_job.status != "completed"
                    or "RELEASE-INSTRUCTIONS-NEW" not in next_job.result["core_snapshot"]
                    or "RELEASE-INSTRUCTIONS-OLD" in next_job.result["core_snapshot"]):
                raise RuntimeError("New task did not use edited instructions")
            return {"original_revision_preserved": True, "new_revision_used": True,
                    "approval_restart_verified": True, "backend": "demo"}

        checks.append(check("offline-assistants:edit-and-approval-recovery", run_instruction_edit_demo))

        def run_attachment_demo(extension="txt") -> dict:
            app_root = temporary_root / ("attachment-app-" + extension)
            agent = create(app_root / "agents" / "files", "developer", "files", "release-check")
            manager = JobManager(app_root)
            conversations = Conversations(manager)
            conversation = conversations.create({
                "request_id": "4" * 32, "agent": str(agent), "backend": "demo",
                "workspace": str(agent / "workspace"), "title": "Attachment release check",
            })
            raw = "RELEASE-FILE-4711: Grüße".encode()
            expected = "RELEASE-FILE-4711"
            if extension == "png":
                raw = (ROOT / "tests" / "fixtures" / "ocr" / "reference.png").read_bytes()
                expected = "OCR REFERENCE 930"
            if extension == "docx":
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as archive:
                    archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>RELEASE-FILE-4711: Grüße</w:t></w:r></w:p></w:body></w:document>')
                raw = buffer.getvalue()
            filename = "reference." + extension
            attachment = conversations.upload(conversation["id"], {
                "request_id": "5" * 32, "name": filename,
                "content_base64": base64.b64encode(raw).decode(),
            })
            if extension == "png" and (attachment.get("extraction_method") != "windows-ocr" or not attachment.get("language")):
                raise RuntimeError("OCR method/language missing from attachment")
            conversations.send(conversation["id"], {"request_id": "6" * 32,
                               "content": "Use the attached reference", "attachment_ids": [attachment["id"]]})
            job = manager.get("6" * 32)
            job.thread.join(15)
            restored = Conversations(JobManager(app_root))
            if job.status != "completed" or expected not in job.result["task"]:
                raise RuntimeError("Attachment did not reach the execution context")
            if restored.download(conversation["id"], attachment["id"])[0] != raw:
                raise RuntimeError("Attachment download changed after restart")
            if (agent / "workspace" / filename).exists():
                raise RuntimeError("Attachment was materialized as executable workspace content")
            return {"context_verified": True, "download_restored": True, "backend": "demo"}

        checks.append(check("offline-attachments:context-and-download-recovery", run_attachment_demo))
        checks.append(check("offline-documents:extraction-and-download-recovery", lambda: run_attachment_demo("docx")))
        if options.windows_ocr:
            checks.append(check("offline-windows-ocr:context-and-download-recovery", lambda: run_attachment_demo("png")))

    for parent in (ROOT / "agents", ROOT / "generated"):
        if not parent.is_dir():
            if parent.name == "agents":
                checks.append({"name": "packs:agents", "ok": False, "error": "directory missing"})
            continue
        for pack in sorted(p for p in parent.iterdir() if p.is_dir() and (p / "agent.json").is_file()):
            checks.append(check(f"pack:{parent.name}/{pack.name}", lambda pack=pack: Catalog(pack).config["id"]))

    failed = [item for item in checks if not item["ok"]]
    report = {
        "status": "passed" if not failed else "failed",
        "offline_only": True,
        "model_tested": False,
        "checks": checks,
        "passed": len(checks) - len(failed),
        "failed": len(failed),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
