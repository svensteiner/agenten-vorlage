import base64
import shutil
import tempfile
import unittest
from pathlib import Path

from agentkit.scaffold import create
from cockpit.conversations import Conversations
from cockpit.server import JobManager


class ColdRestoreTests(unittest.TestCase):
    def test_same_absolute_path_restore_preserves_dialog_attachment_and_approval(self):
        with tempfile.TemporaryDirectory() as parent_name:
            parent = Path(parent_name)
            install = parent / "install"
            backup = parent / "backup"
            agent = create(install / "agents" / "assistant", "developer", "assistant", "Company")
            workspace = agent / "workspace"
            manager = JobManager(install)
            dialogs = Conversations(manager)
            conversation = dialogs.create({
                "request_id": "1" * 32, "agent": str(agent), "backend": "demo",
                "workspace": str(workspace), "title": "Restore fixture",
            })
            attachment = dialogs.upload(conversation["id"], {
                "request_id": "2" * 32, "name": "restore.txt",
                "content_base64": base64.b64encode("RESTORE-ATTACHMENT".encode()).decode(),
            })
            dialogs.send(conversation["id"], {
                "request_id": "3" * 32, "content": "Use attachment",
                "attachment_ids": [attachment["id"]],
            })
            manager.get("3" * 32).thread.join(10)
            self.assertEqual("completed", manager.get("3" * 32).status)
            pending = manager.start({
                "request_id": "4" * 32, "agent": str(agent), "workspace": str(workspace),
                "backend": "demo", "task": "Approval restore", "require_approvals": True,
            })
            pending.thread.join(10)
            pending_snapshot = manager.snapshot(pending)
            approval_id = pending_snapshot["result"]["pending_approval"]["id"]
            self.assertEqual("awaiting_approval", pending_snapshot["status"])
            dialog_before = dialogs.get(conversation["id"])
            completed_bytes = (workspace / "demo-result.md").read_bytes()

            # Stop all writers before making the backup.
            for job in manager.recent(1000):
                if job.thread:
                    job.thread.join(10)
                    self.assertFalse(job.thread.is_alive())
            provider_sentinel = install / "cockpit" / ".runs" / "providers" / "deepseek.json"
            provider_sentinel.parent.mkdir(parents=True, exist_ok=True)
            provider_sentinel.write_text('{"fixture":"must-not-back-up"}', encoding="utf-8")
            def ignore(directory, names):
                if Path(directory).resolve() == (install / "cockpit" / ".runs").resolve():
                    return {"providers"}
                return set()
            shutil.copytree(install, backup, ignore=ignore)
            shutil.rmtree(install)
            shutil.copytree(backup, install)
            self.assertFalse((install / "cockpit" / ".runs" / "providers").exists())

            restored_manager = JobManager(install)
            restored_dialogs = Conversations(restored_manager)
            restored = restored_dialogs.get(conversation["id"])
            self.assertEqual(dialog_before, restored)
            self.assertEqual(attachment, restored["messages"][0]["attachments"][0])
            content, filename = restored_dialogs.download(conversation["id"], attachment["id"])
            self.assertEqual((b"RESTORE-ATTACHMENT", "restore.txt"), (content, filename))
            restored_pending = restored_manager.get(pending.job_id)
            completed_restored = restored_manager.get("3" * 32)
            self.assertEqual("completed", completed_restored.status)
            self.assertIsNone(completed_restored.thread)
            self.assertEqual(completed_bytes, (workspace / "demo-result.md").read_bytes())
            self.assertEqual("awaiting_approval", restored_pending.status)
            self.assertEqual(approval_id, restored_pending.result["pending_approval"]["id"])
            self.assertEqual(pending_snapshot["result"]["pending_approval"],
                             restored_pending.result["pending_approval"])
            self.assertIsNone(restored_pending.thread)
            approved = restored_manager.approval(pending.job_id, approval_id, "approve")
            approved.thread.join(10)
            next_snapshot = restored_manager.snapshot(approved)
            self.assertEqual("awaiting_approval", next_snapshot["status"])
            next_approval = next_snapshot["result"]["pending_approval"]["id"]
            approved = restored_manager.approval(pending.job_id, next_approval, "approve")
            approved.thread.join(10)
            self.assertEqual("completed", restored_manager.snapshot(approved)["status"])


if __name__ == "__main__":
    unittest.main()
