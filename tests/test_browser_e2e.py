from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from agentkit.scaffold import create
from cockpit.conversations import Conversations
from cockpit.server import Job, JobManager, ThreadingHTTPServer, make_handler

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # The regular unit matrix intentionally has no browser dependency.
    sync_playwright = None


@unittest.skipUnless(sync_playwright is not None, "install the e2e extra and Playwright Chromium")
class BrowserReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.agent = create(
            cls.root / "agents" / "programming-agent",
            "developer",
            "programming-agent",
            "AI_Studioxyz",
        )
        cls.workspace = cls.agent / "workspace"
        cls.mobile_workspace = cls.root / ("workspace-" + "x" * 140)
        cls.mobile_workspace.mkdir()
        cls.manager = JobManager(cls.root, cls.root / "state")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.manager))
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        configured_artifacts = os.environ.get("E2E_ARTIFACT_DIR", "").strip()
        cls.artifact_dir = (
            Path(configured_artifacts).resolve()
            if configured_artifacts
            else cls.root / "browser-evidence"
        )
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=5)
        for job in cls.manager.recent():
            if job.thread:
                job.thread.join(timeout=5)
        cls.temp.cleanup()

    def new_page(self, *, width: int = 1280, height: int = 900):
        context = self.browser.new_context(
            accept_downloads=True,
            viewport={"width": width, "height": height},
        )
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        console_errors: list[str] = []
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: console_errors.append(f"pageerror: {error}"))

        def cleanup() -> None:
            stem = self._testMethodName
            try:
                page.screenshot(path=str(self.artifact_dir / f"{stem}.png"), full_page=True)
            finally:
                context.tracing.stop(path=str(self.artifact_dir / f"{stem}.zip"))
                context.close()

        self.addCleanup(cleanup)
        return page, console_errors

    @staticmethod
    def wait_until_connected(page) -> None:
        page.get_by_text("Lokal verbunden", exact=True).wait_for(timeout=10_000)

    def _seed_completed_job(self, result: dict) -> str:
        job_id = uuid.uuid4().hex
        payload = {
            "agent": str(self.agent),
            "backend": "demo",
            "workspace": str(self.workspace),
            "task": "Host provenance display fixture",
        }
        self.manager.jobs[job_id] = Job(
            job_id, payload, status="completed", result=result
        )
        return job_id

    def test_write_provenance_separates_attributed_unmatched_and_legacy_changes(self):
        unmatched_job = self._seed_completed_job({
            "summary": "Model summary is not host evidence.",
            "run_write_provenance": {
                "status": "complete",
                "baseline_status": "captured",
                "changed_by_run": [],
                "changed_without_matching_receipt": ["existing-before-run.py"],
                "unknown_paths": [],
                "unknown_path_count": 0,
                "write_receipt_count": 0,
            },
        })
        page, errors = self.new_page()
        page.goto(f"{self.base_url}/?job={unmatched_job}", wait_until="domcontentloaded")
        self.wait_until_connected(page)
        provenance = page.locator("#writeProvenance")
        provenance.wait_for(state="visible", timeout=5_000)
        text = provenance.inner_text()
        self.assertIn(
            "Keine eigenen Schreibaktionen belegt; vorhandene Änderungen sind kein Implementierungsnachweis",
            text,
        )
        self.assertIn("Unzugeordnete Änderungen", text)
        self.assertIn("existing-before-run.py", text)
        self.assertNotIn("Model summary", text)
        self.assertEqual([], errors)

        attributed_job = self._seed_completed_job({
            "summary": "A file was updated.",
            "run_write_provenance": {
                "status": "complete",
                "baseline_status": "captured",
                "changed_by_run": ["content/updated.md"],
                "changed_without_matching_receipt": [],
                "unknown_paths": [],
                "unknown_path_count": 0,
                "write_receipt_count": 1,
            },
        })
        page.goto(f"{self.base_url}/?job={attributed_job}", wait_until="domcontentloaded")
        provenance = page.locator("#writeProvenance")
        page.wait_for_function(
            "id => document.querySelector('#jobTask')?.textContent && location.search.includes(id)",
            arg=attributed_job,
        )
        provenance.wait_for(state="visible", timeout=5_000)
        self.assertIn("Änderungen, die diesem Lauf zugeordnet sind", provenance.inner_text())
        self.assertIn("content/updated.md", provenance.inner_text())

        legacy_job = self._seed_completed_job({"summary": "Older saved result."})
        page.goto(f"{self.base_url}/?job={legacy_job}", wait_until="domcontentloaded")
        provenance = page.locator("#writeProvenance")
        provenance.wait_for(state="visible", timeout=5_000)
        self.assertIn("Änderungsherkunft nicht belegt", provenance.inner_text())
        self.assertNotIn("Schreibbelege: 0", provenance.inner_text())

        unknown_job = self._seed_completed_job({
            "summary": "Unknown provenance fixture.",
            "run_write_provenance": {
                "status": "unknown",
                "baseline_status": "unknown",
                "changed_by_run": [],
                "changed_without_matching_receipt": [],
                "unknown_paths": [],
                "unknown_path_count": 3,
                "write_receipt_count": 0,
            },
        })
        page.goto(f"{self.base_url}/?job={unknown_job}", wait_until="domcontentloaded")
        provenance = page.locator("#writeProvenance")
        provenance.wait_for(state="visible", timeout=5_000)
        self.assertIn("Änderungsherkunft nicht belegt", provenance.inner_text())
        self.assertIn("Unbekannte Pfade: 3", provenance.inner_text())
        self.assertEqual([], errors)

    def test_write_provenance_renders_paths_as_text_and_is_hidden_in_public_ui(self):
        path = "<img src=x onerror=alert(1)>"
        job_id = self._seed_completed_job({
            "summary": "Host evidence fixture.",
            "run_write_provenance": {
                "status": "partial",
                "baseline_status": "partial",
                "changed_by_run": [path],
                "changed_without_matching_receipt": [],
                "unknown_paths": ["unclassified/file.py"],
                "unknown_path_count": 2,
                "write_receipt_count": 1,
            },
        })
        page, errors = self.new_page()
        page.goto(f"{self.base_url}/?job={job_id}", wait_until="domcontentloaded")
        self.wait_until_connected(page)
        provenance = page.locator("#writeProvenance")
        provenance.wait_for(state="visible", timeout=5_000)
        self.assertIn(path, provenance.inner_text())
        self.assertIn("Unbekannte Pfade: 2", provenance.inner_text())
        self.assertEqual(0, provenance.locator("img").count())

        # Simulate a public configuration paired with an overbroad response;
        # the UI must still keep host-only details hidden.
        def public_config(route):
            response = route.fetch()
            config = response.json()
            config["public_multiuser"] = True
            route.fulfill(response=response, json=config)

        page.route("**/api/config", public_config)
        raw = page.request.get(f"{self.base_url}/api/jobs/{job_id}").json()
        self.assertIn("run_write_provenance", raw["result"])
        page.goto(f"{self.base_url}/?job={job_id}", wait_until="domcontentloaded")
        page.locator("#workspaceTopbar").get_by_text("Öffentlicher Arbeitsbereich").wait_for(timeout=5_000)
        self.assertTrue(page.locator("#writeProvenance").evaluate("node => node.hidden"))
        self.assertNotIn(path, page.locator("body").inner_text())
        self.assertEqual([], errors)

    def test_persisted_conversation_shows_host_provenance_separately(self):
        conversations = Conversations(self.manager)
        conversation = conversations.create({
            "request_id": uuid.uuid4().hex,
            "title": "Provenance chat fixture",
            "agent": str(self.agent),
            "workspace": str(self.workspace),
            "backend": "demo",
        })
        conversation_id = conversation["id"]
        conversations.send(conversation_id, {
            "content": "A conversation with write evidence",
            "request_id": uuid.uuid4().hex,
            "run_write_provenance": {
                "status": "complete",
                "baseline_status": "captured",
                "changed_by_run": ["forged.txt"],
                "changed_without_matching_receipt": [],
                "unknown_paths": [],
                "unknown_path_count": 0,
                "write_receipt_count": 99,
            },
        })
        turn_id = conversations.get(conversation_id)["messages"][0]["id"]
        job = self.manager.get(turn_id)
        job.thread.join(10)
        job.result["run_write_provenance"] = {
            "status": "complete",
            "baseline_status": "captured",
            "changed_by_run": ["content/conversation.md"],
            "changed_without_matching_receipt": [],
            "unknown_paths": [],
            "unknown_path_count": 0,
            "write_receipt_count": 1,
        }
        self.manager._persist(job)

        page, errors = self.new_page()
        page.add_init_script(
            f"sessionStorage.setItem('ai-studio-chat-current', {json.dumps(conversation_id)})"
        )
        page.goto(self.base_url + "/chat", wait_until="domcontentloaded")
        page.get_by_text("Lokal verbunden", exact=True).wait_for(timeout=10_000)
        note = page.locator(".message.assistant .write-provenance")
        note.wait_for(state="visible", timeout=5_000)
        self.assertIn("content/conversation.md", note.inner_text())
        self.assertIn("diesem Lauf zugeordnet", note.inner_text())
        user_message = page.locator(".message.user")
        self.assertNotIn("write-provenance", user_message.get_attribute("class"))
        self.assertNotIn("forged.txt", page.locator("#transcript").inner_text())
        self.assertEqual([], errors)

    def test_job_provenance_rejects_unbounded_metadata_as_unknown(self):
        cases = [
            {"changed_by_run": [f"src/file-{index}.py" for index in range(65)]},
            {"changed_by_run": ["x" * 501]},
            {"write_receipt_count": 49},
            {"unknown_path_count": 65},
        ]
        page, errors = self.new_page()
        for invalid_fields in cases:
            provenance = {
                "status": "complete",
                "baseline_status": "captured",
                "changed_by_run": [],
                "changed_without_matching_receipt": [],
                "unknown_paths": [],
                "unknown_path_count": 0,
                "write_receipt_count": 0,
                **invalid_fields,
            }
            job_id = self._seed_completed_job({"run_write_provenance": provenance})
            page.goto(f"{self.base_url}/?job={job_id}", wait_until="domcontentloaded")
            panel = page.locator("#writeProvenance")
            panel.wait_for(state="visible", timeout=5_000)
            self.assertIn("Änderungsherkunft nicht belegt", panel.inner_text())
            self.assertNotIn("Schreibbelege:", panel.inner_text())
            self.assertNotIn("src/file-0.py", panel.inner_text())
        self.assertEqual([], errors)

    def test_provider_settings_switches_to_anthropic_without_console_errors(self):
        page, errors = self.new_page()
        page.goto(self.base_url + "/settings")
        try:
            self.wait_until_connected(page)
        except Exception as exc:
            self.fail(f"Settings did not connect: {errors}; notice={page.locator('#notice').text_content()}; {exc}")
        page.locator("#providerSelect").wait_for(state="visible")
        with page.expect_response(lambda response: "/api/providers/anthropic" in response.url) as pending:
            page.locator("#providerSelect").select_option("anthropic")
        self.assertEqual(200, pending.value.status)
        self.assertEqual("anthropic", page.locator("#providerSelect").input_value())
        self.assertEqual("", page.locator("#apiKey").input_value())
        self.assertEqual([], errors)

    def assert_accessible_controls(self, page) -> None:
        unnamed = page.evaluate(
            r"""
            () => [...document.querySelectorAll('button,a,input,select,textarea')]
              .filter((element) => {
                if (element.matches('input[type="hidden"]')) return false;
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden'
                  && rect.width > 0 && rect.height > 0;
              })
              .filter((element) => {
                const labelledBy = (element.getAttribute('aria-labelledby') || '')
                  .split(/\s+/).filter(Boolean)
                  .map((id) => document.getElementById(id)?.textContent || '').join(' ');
                const explicit = element.id
                  ? document.querySelector(`label[for="${CSS.escape(element.id)}"]`)?.textContent || ''
                  : '';
                const wrapping = element.closest('label')?.textContent || '';
                const native = ['BUTTON', 'A'].includes(element.tagName)
                  ? element.textContent || ''
                  : element.matches('input[type="button"],input[type="submit"]')
                    ? element.value || '' : '';
                return ![
                  element.getAttribute('aria-label') || '', labelledBy, explicit,
                  wrapping, native, element.getAttribute('title') || ''
                ].some((value) => value.trim());
              })
              .map((element) => `${element.tagName.toLowerCase()}#${element.id || '(none)'}`)
            """
        )
        self.assertEqual([], unnamed)
        self.assertEqual(1, page.locator("h1").count())

    def test_navigation_accessibility_and_mobile_reflow(self):
        page, console_errors = self.new_page(width=390, height=844)
        response = page.request.post(
            self.base_url + "/api/conversations",
            data={
                "request_id": uuid.uuid4().hex,
                "agent": str(self.agent),
                "workspace": str(self.mobile_workspace),
                "backend": "demo",
                "model": "",
                "title": "Mobile Reflow",
                "require_approvals": False,
            },
        )
        self.assertEqual(201, response.status, response.text())
        expected_workspace = response.json()["workspace"]
        for path, title in (
            ("/", "AI Studio · Dein lokaler Arbeitsraum"),
            ("/chat", "AI Studio · Arbeitsdialog"),
            ("/settings", "AI Studio · Provider-Einstellungen"),
            ("/assistants", "AI Studio · Assistenten verwalten"),
        ):
            with self.subTest(path=path):
                page.goto(self.base_url + path, wait_until="domcontentloaded")
                self.wait_until_connected(page)
                page.locator("h1").wait_for(timeout=5_000)
                self.assertEqual(title, page.title())
                self.assert_accessible_controls(page)
                if path == "/chat":
                    workspace_chip = page.locator("#conversationChips .chip").nth(2)
                    workspace_chip.wait_for(state="visible", timeout=5_000)
                    self.assertEqual(expected_workspace, workspace_chip.inner_text())
                    bounds = workspace_chip.bounding_box()
                    self.assertIsNotNone(bounds)
                    self.assertGreater(bounds["width"], 0)
                    self.assertLessEqual(bounds["x"] + bounds["width"], 391)
                layout = page.evaluate(
                    """
                    () => ({
                      scrollWidth: document.documentElement.scrollWidth,
                      clientWidth: document.documentElement.clientWidth,
                      offenders: [...document.querySelectorAll('body *')]
                        .filter((element) => {
                          const rect = element.getBoundingClientRect();
                          const style = getComputedStyle(element);
                          return style.display !== 'none' && style.visibility !== 'hidden'
                            && (rect.right > document.documentElement.clientWidth + 1 || rect.left < -1);
                        })
                        .slice(0, 10)
                        .map((element) => ({
                          tag: element.tagName.toLowerCase(), id: element.id,
                          className: element.className,
                          left: element.getBoundingClientRect().left,
                          right: element.getBoundingClientRect().right
                        }))
                    })
                    """
                )
                self.assertLessEqual(
                    layout["scrollWidth"], layout["clientWidth"] + 1, layout
                )
        self.assertEqual([], console_errors)

    def test_demo_workflow_download_and_reload(self):
        page, console_errors = self.new_page()
        page.goto(self.base_url + "/", wait_until="domcontentloaded")
        self.wait_until_connected(page)
        page.locator("#agent").select_option(label="programming-agent")
        page.locator("#backend").select_option("demo")
        page.locator("#workspace").fill(str(self.workspace))
        page.locator("#task").fill(
            "Automatisierte Browser-Abnahme: Umsetzung, Review, Korrektur und Download."
        )
        with page.expect_response(
            lambda response: response.url == self.base_url + "/api/jobs"
            and response.request.method == "POST",
            timeout=10_000,
        ) as response_info:
            page.locator("#run").click()
        job_id = response_info.value.json()["job_id"]
        self.assertRegex(job_id, r"^[0-9a-f]{32}$")

        approval = page.locator("#approvalCard")
        approval.wait_for(state="visible", timeout=10_000)
        self.assertEqual("write_file", page.locator("#approvalTool").inner_text())
        first_arguments = page.locator("#approvalArguments").inner_text()
        page.locator("#approveAction").click()
        page.wait_for_function(
            """
            (firstArguments) => {
              const card = document.querySelector('#approvalCard');
              const args = document.querySelector('#approvalArguments');
              const trace = document.querySelector('#workflowTrace');
              return card && !card.hidden && args && args.textContent !== firstArguments
                && trace && trace.textContent.includes('Überarbeitung nötig');
            }
            """,
            arg=first_arguments,
            timeout=15_000,
        )
        self.assertIn(page.locator("#approvalTool").inner_text(), {"write_file", "edit_file"})
        page.locator("#approveAction").click()
        page.wait_for_function(
            "() => document.querySelector('#jobStatus')?.textContent.trim() === 'Abgeschlossen'",
            timeout=15_000,
        )

        timeline = page.locator("#timeline").inner_text()
        self.assertIn("Missing acceptance marker; repair required.", timeline)
        self.assertIn("Acceptance marker verified.", timeline)
        self.assertIn("Überarbeitung nötig", page.locator("#workflowTrace").inner_text())
        artifact = page.locator("#artifacts a", has_text="demo-result.md")
        artifact.wait_for(state="visible", timeout=5_000)
        with page.expect_download(timeout=5_000) as download_info:
            artifact.click()
        downloaded = Path(download_info.value.path()).read_bytes()
        self.assertIn(b"ACCEPTED", downloaded)

        page.goto(self.base_url + "/?job=" + job_id, wait_until="domcontentloaded")
        self.wait_until_connected(page)
        page.wait_for_function(
            "() => document.querySelector('#jobStatus')?.textContent.trim() === 'Abgeschlossen'",
            timeout=10_000,
        )
        self.assertEqual(job_id, parse_qs(urlsplit(page.url).query)["job"][0])
        page.locator("#artifacts a", has_text="demo-result.md").wait_for(state="visible")
        page.reload(wait_until="domcontentloaded")
        self.wait_until_connected(page)
        page.wait_for_function(
            "() => document.querySelector('#jobStatus')?.textContent.trim() === 'Abgeschlossen'",
            timeout=10_000,
        )
        self.assertEqual([], console_errors)

    def test_first_run_preferences_select_agent_workspace_codex_and_task(self):
        preferred_workspace = self.root / "marketing-workspace"
        preferred_workspace.mkdir(exist_ok=True)
        manager = JobManager(
            self.root,
            self.root / "preferred-state",
            default_workspace=preferred_workspace,
            preferred_agent="programming-agent",
            preferred_backend="codex",
            starter_task="Create a measured seven-day growth plan.",
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(manager))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def cleanup_server() -> None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.addCleanup(cleanup_server)
        page, console_errors = self.new_page()
        with patch(
            "cockpit.server.codex_readiness",
            return_value={
                "installed": True,
                "credentials_present": True,
                "sandbox_configured": True,
            },
        ):
            page.goto(
                f"http://127.0.0.1:{server.server_port}/",
                wait_until="domcontentloaded",
            )
            self.wait_until_connected(page)
            page.wait_for_function("() => document.querySelector('#backend')?.value === 'codex'")
            self.assertEqual(
                "programming-agent",
                page.locator("#agent option:checked").text_content(),
            )
            self.assertEqual("codex", page.locator("#backend").input_value())
            self.assertTrue(
                os.path.samefile(
                    preferred_workspace,
                    Path(page.locator("#workspace").input_value()),
                )
            )
            self.assertEqual(
                "Create a measured seven-day growth plan.",
                page.locator("#task").input_value(),
            )

            page.goto(
                f"http://127.0.0.1:{server.server_port}/chat",
                wait_until="domcontentloaded",
            )
            self.wait_until_connected(page)
            page.wait_for_function("() => document.querySelector('#backend')?.value === 'codex'")
            self.assertEqual(
                "programming-agent",
                page.locator("#agent option:checked").text_content(),
            )
            self.assertTrue(
                os.path.samefile(
                    preferred_workspace,
                    Path(page.locator("#workspace").input_value()),
                )
            )
            self.assertEqual(
                "Create a measured seven-day growth plan.",
                page.locator("#message").input_value(),
            )
        self.assertEqual([], console_errors)

    def test_assistant_archive_restore_survives_reload(self):
        page, console_errors = self.new_page()
        page.goto(self.base_url + "/assistants", wait_until="domcontentloaded")
        self.wait_until_connected(page)
        archive = page.get_by_role("button", name="Archivieren: programming-agent")
        archive.wait_for(state="visible", timeout=5_000)
        archive.click()
        restore = page.get_by_role("button", name="Wiederherstellen: programming-agent")
        restore.wait_for(state="visible", timeout=5_000)
        page.reload(wait_until="domcontentloaded")
        self.wait_until_connected(page)
        restore = page.get_by_role("button", name="Wiederherstellen: programming-agent")
        restore.wait_for(state="visible", timeout=5_000)
        restore.click()
        page.get_by_role("button", name="Archivieren: programming-agent").wait_for(
            state="visible", timeout=5_000
        )
        self.assertEqual([], console_errors)


@unittest.skipUnless(sync_playwright is not None, "install the e2e extra and Playwright Chromium")
class ExecutionProfileBrowserJourneyTests(unittest.TestCase):
    """UI/HTTP contract fixture; the scripted backend is not an agent-quality pass."""

    @classmethod
    def setUpClass(cls):
        from cockpit.server import JobManager, ThreadingHTTPServer, make_handler

        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.agents_root = cls.root / "agents"
        cls.agent = create(cls.agents_root / "profile-agent", "developer", "profile-agent", "E2E")
        cls.other_agent = create(cls.agents_root / "other-agent", "developer", "other-agent", "E2E")
        cls.workspace = cls.root / "project"
        cls.workspace.mkdir()
        cls.other_workspace = cls.root / "other-project"
        cls.other_workspace.mkdir()

        path_manager = JobManager(
            template_root=cls.root,
            state_dir=cls.root / "path-state",
            agent_roots=(cls.agents_root,),
            generated_root=cls.agents_root,
        )
        cls.agent_ref = path_manager._agent_reference(path_manager._agent_path(str(cls.agent)))
        cls.other_agent_ref = path_manager._agent_reference(
            path_manager._agent_path(str(cls.other_agent))
        )
        cls.workspace_ref = path_manager._workspace_reference(
            path_manager._workspace_path(str(cls.workspace))
        )
        cls.other_workspace_ref = path_manager._workspace_reference(
            path_manager._workspace_path(str(cls.other_workspace))
        )

        test_bytes = b"def test_smoke():\n    assert True\n"
        test_file = cls.workspace / "tests" / "test_smoke.py"
        test_file.parent.mkdir()
        test_file.write_bytes(test_bytes)
        cls.test_manifest = cls.root / "operator-tests.json"
        cls.test_manifest.write_text(json.dumps({
            "version": 1,
            "image_ref": "python@sha256:" + "a" * 64,
            "image_id": "sha256:" + "b" * 64,
            "dependency_lock_sha256": "c" * 64,
            "docker_transport": "native",
            "test_files": [{
                "path": "tests/test_smoke.py",
                "sha256": hashlib.sha256(test_bytes).hexdigest(),
            }],
            "support_files": [],
            "expected_test_count": 1,
            "snapshot_paths": ["tests/test_smoke.py"],
        }), encoding="utf-8")
        cls.profile_path = cls.root / "execution-profiles.json"
        cls.profile_path.write_text(json.dumps({
            "version": 1,
            "profiles": [{
                "id": "profile-agent-safe",
                "label": "Profile Agent · bounded test profile",
                "agent": cls.agent_ref,
                "workspace": cls.workspace_ref,
                "backend": "codex",
                "write_paths": ["notes.md"],
                "test_manifest": str(cls.test_manifest),
                "host_autonomous": True,
            }],
        }), encoding="utf-8")

        cls.manager = JobManager(
            template_root=cls.root,
            state_dir=cls.root / "state",
            agent_roots=(cls.agents_root,),
            generated_root=cls.agents_root,
            execution_profiles_path=cls.profile_path,
        )
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.manager))
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.artifact_dir = Path(__file__).resolve().parents[1] / ".diagnostics" / "execution-profile-browser"
        cls.artifact_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=5)
        for job in cls.manager.recent(1000):
            if job.thread:
                job.thread.join(timeout=5)
        cls.browser.close()
        cls.playwright.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1280, "height": 900})
        self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        self.page = self.context.new_page()
        self.console_errors = []
        self.page.on("console", lambda message: self.console_errors.append(message.text)
                     if message.type == "error" else None)
        self.page.on("pageerror", lambda error: self.console_errors.append(f"pageerror: {error}"))
        self.addCleanup(self._close_page)

    def _close_page(self):
        try:
            self.page.screenshot(
                path=str(self.artifact_dir / "execution-profile-final.png"), full_page=True
            )
        finally:
            self.context.tracing.stop(
                path=str(self.artifact_dir / "execution-profile-journey.zip")
            )
            self.context.close()

    def _select_profile(self, path: str, *, assert_chips: bool = False):
        page = self.page
        page.locator("#agent").select_option(path)
        page.locator("#backend").select_option("codex")
        page.locator("#workspace").fill(self.workspace_ref)
        option = page.locator('#executionProfile option[value="profile-agent-safe"]')
        option.wait_for(state="attached", timeout=5_000)
        page.locator("#executionProfile").select_option("profile-agent-safe")
        self.assertIn("notes.md", page.locator("#executionProfile option:checked").inner_text())
        self.assertIn("Tests: 1", page.locator("#executionProfile option:checked").inner_text())
        self.assertIn("Gebunden an profile-agent", page.locator("#executionProfileHint").inner_text())
        self.assertIn("Hostprofil", page.locator("#executionProfileHint").inner_text())
        self.assertEqual(path, page.locator("#agent").input_value())
        self.assertEqual("codex", page.locator("#backend").input_value())
        self.assertEqual(self.workspace_ref, page.locator("#workspace").input_value())
        if assert_chips:
            self._assert_profile_chips()

    def _assert_profile_chips(self):
        chips = self.page.locator("#conversationChips .chip")
        self.assertEqual("profile-agent", chips.nth(0).inner_text())
        self.assertEqual("Codex CLI", chips.nth(1).inner_text())
        self.assertEqual(self.workspace_ref, chips.nth(2).inner_text())
        self.assertIn("Profile Agent", chips.nth(3).inner_text())

    def test_curated_profile_journey_and_recovery_payload_binding(self):
        from unittest.mock import patch

        class ScriptedBackend:
            """Deterministic fixture that blocks, then blocks again after resume."""
            name = "codex"
            supports_action_approvals = True
            supports_write_policy = True
            supports_isolated_tests = True
            approval_identity = "scripted-ui-contract-fixture"

            def __init__(self, model=None):
                self.model = model

            @staticmethod
            def decide(context, timeout):
                history = context["history"]
                if not history or (history[-1].get("report", {}).get("status") == "blocked"
                                   and context.get("feedback")):
                    return {"action": "delegate", "role": "developer", "skills": [],
                            "task": "scripted contract step", "reason": "browser fixture"}
                if history[-1].get("decision", {}).get("role") == "developer":
                    return {"action": "delegate", "role": "reviewer", "skills": [],
                            "task": "scripted contract review", "reason": "browser fixture"}
                return {"action": "blocked", "role": "", "skills": [],
                        "task": "Fixture intentionally blocks; no agent result is claimed.",
                        "reason": "browser fixture"}

            @staticmethod
            def execute(decision, context, timeout):
                return {"status": "blocked", "summary": "Fixture intentionally blocks for recovery testing.",
                        "artifacts": [], "evidence": ["scripted fixture only"],
                        "next_actions": ["Resume the same bound job in this test."]}

        page = self.page
        with patch("cockpit.server.CodexBackend", ScriptedBackend), patch(
            "cockpit.server.codex_readiness",
            return_value={"installed": True, "credentials_present": True,
                          "sandbox_configured": True},
        ):
            page.goto(self.base_url + "/", wait_until="domcontentloaded")
            page.get_by_text("Lokal verbunden", exact=True).wait_for(timeout=10_000)
            page.locator("#executionProfileField").wait_for(state="visible")

            self._select_profile(self.agent_ref)
            page.screenshot(path=str(self.artifact_dir / "execution-profile-index-selected.png"),
                            full_page=True)

            # The profile is offered only for its exact host-bound triple.
            page.locator("#workspace").fill(self.other_workspace_ref)
            self.assertEqual(0, page.locator('#executionProfile option[value="profile-agent-safe"]').count())
            page.locator("#workspace").fill(self.workspace_ref)
            page.locator("#backend").select_option("demo")
            self.assertEqual(0, page.locator('#executionProfile option[value="profile-agent-safe"]').count())
            page.locator("#backend").select_option("codex")
            page.locator("#agent").select_option(self.other_agent_ref)
            self.assertEqual(0, page.locator('#executionProfile option[value="profile-agent-safe"]').count())
            self._select_profile(self.agent_ref)

            forged = page.request.post(self.base_url + "/api/jobs", data={
                "agent": self.agent_ref, "workspace": self.workspace_ref, "backend": "codex",
                "task": "must be rejected", "request_id": "d" * 32,
                "execution_profile_id": "profile-agent-safe", "write_paths": ["outside.py"],
                "test_manifest": str(self.test_manifest), "host_autonomous": False,
            })
            self.assertEqual(400, forged.status)
            self.assertIsNone(self.manager.get("d" * 32))

            page.locator("#task").fill("Exercise curated-profile request and resume binding.")
            with page.expect_response(
                lambda response: response.url == self.base_url + "/api/jobs"
                and response.request.method == "POST", timeout=10_000,
            ) as started:
                page.locator("#run").click()
            start_response = started.value
            self.assertEqual(202, start_response.status)
            job = start_response.json()
            job_id = job["job_id"]
            start_payload = json.loads(start_response.request.post_data)
            self.assertEqual("profile-agent-safe", start_payload["execution_profile_id"])
            self.assertNotIn("require_approvals", start_payload)
            self.assertFalse(set(start_payload) & {
                "execution_profile_sha256", "write_policy", "test_execution_policy",
                "write_paths", "test_manifest", "host_autonomous",
            })
            self.assertEqual(self.agent_ref, start_payload["agent"])
            self.assertEqual(self.workspace_ref, start_payload["workspace"])
            self.assertEqual("codex", start_payload["backend"])

            page.wait_for_function(
                "id => fetch(`/api/jobs/${id}`).then(r => r.json()).then(j => j.status === 'blocked')",
                arg=job_id, timeout=10_000,
            )
            page.locator("#resumeForm").wait_for(state="visible", timeout=5_000)
            self.assertEqual("profile-agent-safe", self.manager.get(job_id).payload["execution_profile_id"])
            page.locator("#feedback").fill("Resume the same profile-bound run.")
            with page.expect_response(
                lambda response: response.url.endswith(f"/api/jobs/{job_id}/resume")
                and response.request.method == "POST", timeout=10_000,
            ) as resumed:
                page.locator("#resume").click()
            resume_response = resumed.value
            self.assertEqual(202, resume_response.status)
            resume_payload = json.loads(resume_response.request.post_data)
            self.assertEqual({"feedback", "acknowledge_interruption"}, set(resume_payload))
            self.assertNotIn("execution_profile_id", resume_payload)
            page.wait_for_function(
                "id => fetch(`/api/jobs/${id}`).then(r => r.json()).then(j => j.status === 'blocked')",
                arg=job_id, timeout=10_000,
            )
            self.assertEqual("profile-agent-safe", self.manager.get(job_id).payload["execution_profile_id"])
            self.assertTrue(self.manager.get(job_id).payload["execution_profile_sha256"])

            # Conversation creation sends just the profile ID; persisted metadata
            # survives a page reload, while the worker remains a blocking fixture.
            page.goto(self.base_url + "/chat", wait_until="domcontentloaded")
            page.get_by_text("Lokal verbunden", exact=True).wait_for(timeout=10_000)
            page.locator("#settingsCard").wait_for(state="visible", timeout=5_000)
            self._select_profile(self.agent_ref, assert_chips=True)
            page.locator("#title").fill("Profile persistence fixture")
            page.locator("#message").fill("Create a conversation with the selected host profile.")
            page.screenshot(path=str(self.artifact_dir / "execution-profile-chat-selected.png"),
                            full_page=True)
            with page.expect_response(
                lambda response: response.url == self.base_url + "/api/conversations"
                and response.request.method == "POST", timeout=10_000,
            ) as created:
                page.locator("#send").click()
            create_response = created.value
            self.assertEqual(201, create_response.status)
            conversation = create_response.json()
            conversation_id = conversation["id"]
            create_payload = json.loads(create_response.request.post_data)
            self.assertEqual("profile-agent-safe", create_payload["execution_profile_id"])
            self.assertFalse(set(create_payload) & {
                "execution_profile_sha256", "write_policy", "test_execution_policy",
                "write_paths", "test_manifest", "host_autonomous",
            })
            self.assertEqual("profile-agent-safe", conversation["execution_profile"]["id"])
            self.assertEqual(["notes.md"], conversation["execution_profile"]["write_paths"])
            self.assertEqual(1, conversation["execution_profile"]["tests"]["expected_test_count"])

            page.wait_for_function(
                "() => document.querySelector('#transcript')?.textContent.includes('Klärung erforderlich')",
                timeout=10_000,
            )
            page.reload(wait_until="domcontentloaded")
            page.get_by_text("Lokal verbunden", exact=True).wait_for(timeout=10_000)
            page.wait_for_function(
                "() => !document.querySelector('#conversationView')?.hidden "
                "&& document.querySelector('#conversationTitle')?.textContent === 'Profile persistence fixture'",
                timeout=10_000,
            )
            page.wait_for_function(
                "id => fetch(`/api/conversations/${id}`).then(r => r.json()).then(c => "
                "c.execution_profile?.id === 'profile-agent-safe')",
                arg=conversation_id, timeout=10_000,
            )
            persisted = page.request.get(self.base_url + f"/api/conversations/{conversation_id}").json()
            self.assertEqual("profile-agent-safe", persisted["execution_profile"]["id"])
            self._assert_profile_chips()
            page.screenshot(path=str(self.artifact_dir / "execution-profile-chat-reloaded.png"),
                            full_page=True)

            page.evaluate("pending => sessionStorage.setItem('ai-studio-chat-pending', JSON.stringify(pending))", {
                "kind": "conversation", "request_id": "f" * 32, "signature": "fixture",
                "payload": {
                    "agent": self.agent_ref, "workspace": self.workspace_ref,
                    "backend": "codex", "model": "", "title": "Recovered profile draft",
                    "execution_profile_id": "profile-agent-safe", "content": "Recovered draft",
                    "attachments": [],
                },
            })
            page.reload(wait_until="domcontentloaded")
            page.get_by_text("Lokal verbunden", exact=True).wait_for(timeout=10_000)
            page.wait_for_function(
                "() => !document.querySelector('#conversationView')?.hidden "
                "&& document.querySelector('#title')?.value === 'Recovered profile draft'",
                timeout=10_000,
            )
            self.assertEqual(self.agent_ref, page.locator("#agent").input_value())
            self.assertEqual("codex", page.locator("#backend").input_value())
            self.assertEqual(self.workspace_ref, page.locator("#workspace").input_value())
            self.assertEqual("profile-agent-safe", page.locator("#executionProfile").input_value())
            self._assert_profile_chips()

            conversation_posts = []
            page.on("request", lambda request: conversation_posts.append(request.url)
                    if request.method == "POST" and request.url.endswith("/api/conversations") else None)
            page.evaluate("pending => sessionStorage.setItem('ai-studio-chat-pending', JSON.stringify(pending))", {
                "kind": "conversation", "request_id": "1" * 32, "signature": "missing-profile-fixture",
                "payload": {
                    "agent": self.agent_ref, "workspace": self.workspace_ref,
                    "backend": "codex", "model": "", "title": "Unavailable profile draft",
                    "execution_profile_id": "profile-no-longer-registered", "content": "Do not auto-send",
                    "attachments": [],
                },
            })
            page.reload(wait_until="domcontentloaded")
            page.get_by_text("Lokal verbunden", exact=True).wait_for(timeout=10_000)
            page.wait_for_function(
                "() => !document.querySelector('#conversationView')?.hidden "
                "&& document.querySelector('#title')?.value === 'Unavailable profile draft'",
                timeout=10_000,
            )
            self.assertEqual("", page.locator("#executionProfile").input_value())
            self.assertNotIn("Profile Agent", page.locator("#conversationChips").inner_text())
            self.assertIn("nicht mehr verfügbar", page.locator("#notice").inner_text())
            self.assertIn("nicht bestätigte Dialogerstellung", page.locator("#notice").inner_text())
            self.assertEqual([], conversation_posts)

            forged_conversation = page.request.post(self.base_url + "/api/conversations", data={
                "request_id": "e" * 32, "agent": self.agent_ref, "workspace": self.workspace_ref,
                "backend": "codex", "title": "forgery", "execution_profile_id": "profile-agent-safe",
                "write_paths": ["outside.py"],
            })
            self.assertEqual(400, forged_conversation.status)
            self.assertEqual([], self.console_errors)
