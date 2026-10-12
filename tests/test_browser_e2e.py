from __future__ import annotations

import os
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from agentkit.scaffold import create
from cockpit.server import JobManager, ThreadingHTTPServer, make_handler

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
