from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.backends import (
    CodexBackend,
    DeepSeekBackend,
    DemoBackend,
    _NoProviderRedirect,
    run_process,
)
from agentkit.approvals import action_digest, replay_action_digest
from agentkit.catalog import Catalog, skill_metadata
from agentkit.contracts import ContractError, LIBRARY, read_json
from agentkit.engine import Engine
from agentkit.integrations import issue_to_task, native_prompt, result_to_update
from agentkit.scaffold import add_skill, create
from agentkit.storage import lock, save


def decision(action="delegate", role="developer", skills=None):
    return {
        "action": action,
        "role": role,
        "skills": skills or [],
        "task": "Bounded task",
        "reason": "Evidence gap",
    }


def report(status="success", evidence=None):
    return {
        "status": status,
        "summary": "Observation",
        "artifacts": [],
        "evidence": ["Inspected current acceptance criteria"]
        if evidence is None
        else evidence,
        "next_actions": [],
    }


class SequenceBackend:
    name = "test"

    def __init__(self, decisions, reports=()):
        self.decisions = iter(decisions)
        self.reports = iter(reports)
        self.calls = 0

    def decide(self, context, timeout):
        return next(self.decisions)

    def execute(self, choice, context, timeout):
        self.calls += 1
        value = next(self.reports)
        if isinstance(value, Exception):
            raise value
        return value


class AgentKitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agent", "developer", "cto-dev", "AI_Studioxyz")
        self.workspace = self.agent / "workspace"

    def tearDown(self):
        self.temp.cleanup()

    def run_backend(self, backend):
        return Engine(self.agent, self.workspace, backend).run(
            "Build a verified deliverable"
        )

    def change_limits(self, **changes):
        cfg = read_json(self.agent / "agent.json")
        cfg["limits"].update(changes)
        save(self.agent / "agent.json", cfg)

    def test_all_profiles_generate_valid_portable_packs(self):
        for name in read_json(LIBRARY / "profiles.json"):
            with self.subTest(name=name):
                target = create(self.root / name, name, name, "Example Company")
                self.assertTrue(Catalog(target).roles)
                self.assertTrue((target / "STATUS.md").is_file())
                for skill in (target / ".agents/skills").glob("*/SKILL.md"):
                    skill_metadata(skill)

    def test_status_is_first_class_handoff_in_native_prompt(self):
        prompt = native_prompt(self.agent, "Inspect the current project")
        self.assertIn("Read STATUS.md first", prompt)

    def test_existing_target_and_invalid_id_never_overwritten(self):
        before = (self.agent / "agent.json").read_bytes()
        with self.assertRaises(ContractError):
            create(self.agent, "developer", "other", "Company")
        with self.assertRaises(ContractError):
            create(self.root / "other", "developer", "../escape", "Company")
        self.assertEqual(before, (self.agent / "agent.json").read_bytes())

    def test_demo_replans_from_failed_review(self):
        state = self.run_backend(DemoBackend())
        self.assertEqual("completed", state["status"])
        self.assertEqual(
            ["developer", "reviewer", "developer", "reviewer", ""],
            [x["decision"]["role"] for x in state["history"]],
        )
        self.assertEqual("needs_revision", state["history"][1]["report"]["status"])
        self.assertIn("ACCEPTED", (self.workspace / "demo-result.md").read_text())
        self.assertEqual(1, state["failures"])

    def test_bmd_demo_uses_domain_roles(self):
        agent = create(
            self.root / "bmd-agent", "bmd-tax-advisor", "bmd-tax-advisor", "Example Company"
        )
        workspace = agent / "workspace"
        state = Engine(agent, workspace, DemoBackend()).run(
            "Prepare a controlled BMD workflow artifact"
        )
        self.assertEqual("completed", state["status"])
        self.assertEqual(
            ["bmd-operator", "tax-reviewer", "bmd-operator", "tax-reviewer", ""],
            [x["decision"]["role"] for x in state["history"]],
        )

    def test_research_can_finish_without_coding_pipeline(self):
        backend = SequenceBackend(
            [decision(role="researcher"), decision("finish", "")], [report()]
        )
        state = self.run_backend(backend)
        self.assertEqual("completed", state["status"])
        self.assertFalse(state["dirty"])

    def test_finish_without_evidence_or_work_is_rejected(self):
        for reports, decisions in [
            ([], [decision("finish", "")]),
            (
                [report(evidence=[])],
                [decision(role="researcher"), decision("finish", "")],
            ),
        ]:
            with self.subTest(reports=reports):
                state = self.run_backend(SequenceBackend(decisions, reports))
                self.assertEqual("blocked", state["status"])
                self.assertIn("evidence", state["history"][-1]["completion_rejected"])

    def test_writes_require_review(self):
        state = self.run_backend(
            SequenceBackend([decision(), decision("finish", "")], [report()])
        )
        self.assertEqual("blocked", state["status"])
        self.assertIn("subsequent review", state["history"][-1]["completion_rejected"])

    def test_premature_finish_replans_to_gather_evidence(self):
        backend = SequenceBackend(
            [decision("finish", ""), decision(role="researcher"), decision("finish", "")],
            [report()],
        )
        original_decide = backend.decide
        observations = []
        def observe(context, timeout):
            observations.append(json.loads(json.dumps(context)))
            return original_decide(context, timeout)
        backend.decide = observe
        state = self.run_backend(backend)
        self.assertEqual("completed", state["status"])
        self.assertEqual(1, state["failures"])
        self.assertEqual(1, backend.calls)
        self.assertIn("evidence", observations[1]["history"][-1]["completion_rejected"])
        self.assertEqual(observations[0]["task"], observations[1]["task"])
        self.assertEqual(observations[0]["feedback"], observations[1]["feedback"])
        self.assertIsNone(state["in_flight"])

    def test_premature_finish_replans_to_independent_review(self):
        backend = SequenceBackend(
            [decision(), decision("finish", ""), decision(role="reviewer"), decision("finish", "")],
            [report(), report()],
        )
        state = self.run_backend(backend)
        self.assertEqual("completed", state["status"])
        self.assertEqual(2, backend.calls)
        self.assertTrue(state["reviewed"])
        self.assertEqual(1, state["failures"])
        self.assertIn("review", state["history"][1]["completion_rejected"])

    def test_repeated_premature_finish_exhausts_failure_budget_without_execution(self):
        self.change_limits(max_failures=2)
        backend = SequenceBackend([decision("finish", "")] * 5)
        state = self.run_backend(backend)
        self.assertEqual("blocked", state["status"])
        self.assertIn("Failure budget", state["summary"])
        self.assertEqual(2, state["failures"])
        self.assertEqual(2, state["steps"])
        self.assertEqual(0, backend.calls)
        self.assertIsNone(state["in_flight"])

    def test_edit_invalidates_previous_review(self):
        choices = [
            decision(),
            decision(role="reviewer"),
            decision(),
            decision("finish", ""),
        ]
        state = self.run_backend(
            SequenceBackend(choices, [report(), report(), report()])
        )
        self.assertEqual("blocked", state["status"])
        self.assertFalse(state["reviewed"])

    def test_failed_review_invalidates_successful_review(self):
        choices = [
            decision(),
            decision(role="reviewer"),
            decision(role="reviewer"),
            decision("finish", ""),
        ]
        state = self.run_backend(
            SequenceBackend(choices, [report(), report(), report("needs_revision")])
        )
        self.assertEqual("blocked", state["status"])
        self.assertFalse(state["reviewed"])

    def test_unassigned_skill_or_unknown_role_never_executes(self):
        for choice in [
            decision(skills=["customer-response"]),
            decision(role="../../other"),
        ]:
            backend = SequenceBackend([choice])
            state = self.run_backend(backend)
            self.assertEqual("blocked", state["status"])
            self.assertEqual(0, backend.calls)

    def test_invalid_model_json_fails_closed(self):
        choice = decision()
        choice["execute_shell"] = "arbitrary command"
        backend = SequenceBackend([choice])
        state = self.run_backend(backend)
        self.assertEqual("blocked", state["status"])
        self.assertEqual(0, backend.calls)

    def test_artifact_must_exist_and_stay_in_workspace(self):
        internal = self.workspace / ".git" / "config"
        internal.parent.mkdir()
        internal.write_text("secret", encoding="utf-8")
        for artifact in [
            "missing.txt",
            "../agent.json",
            str(self.agent / "agent.json"),
            ".git/config",
        ]:
            value = report()
            value["artifacts"] = [artifact]
            state = self.run_backend(SequenceBackend([decision()], [value]))
            self.assertEqual("blocked", state["status"])
            self.assertIsNotNone(state["in_flight"])

    def test_step_budget_is_enforced(self):
        self.change_limits(max_steps=1)
        state = self.run_backend(
            SequenceBackend([decision(role="researcher")], [report()])
        )
        self.assertEqual("blocked", state["status"])
        self.assertIn("Step budget", state["summary"])

    def test_failure_budget_is_enforced(self):
        self.change_limits(max_failures=1)
        state = self.run_backend(
            SequenceBackend([decision()], [report("needs_revision")])
        )
        self.assertIn("Failure budget", state["summary"])

    def test_manual_feedback_starts_new_failure_epoch_without_erasing_audit(self):
        self.change_limits(max_failures=1)
        state = self.run_backend(
            SequenceBackend([decision()], [report("needs_revision")])
        )
        self.assertEqual("blocked", state["status"])
        self.assertEqual(1, state["failures"])
        resumed = Engine(
            self.agent,
            self.workspace,
            SequenceBackend(
                [decision(role="reviewer"), decision("finish", "")],
                [report()],
            ),
        ).run(
            "",
            run_dir=self.agent / ".runs" / state["run_id"],
            feedback="The blocker was resolved; inspect the fresh evidence.",
        )
        self.assertEqual("completed", resumed["status"])
        self.assertEqual(1, resumed["failures"])
        self.assertTrue(resumed["reviewed"])

    def test_context_budget_blocks_before_worker(self):
        self.change_limits(max_context_chars=1000)
        backend = SequenceBackend([decision()])
        state = self.run_backend(backend)
        self.assertEqual(0, backend.calls)
        self.assertIn("Context budget", state["summary"])

    def test_interrupted_worker_is_not_automatically_replayed(self):
        state = self.run_backend(
            SequenceBackend([decision()], [RuntimeError("simulated crash")])
        )
        folder = self.agent / ".runs" / state["run_id"]
        backend = SequenceBackend([decision("blocked", "")])
        engine = Engine(self.agent, self.workspace, backend)
        with self.assertRaises(ContractError):
            engine.run("", run_dir=folder, feedback="Inspect first")
        resumed = engine.run(
            "",
            run_dir=folder,
            feedback="Inspected output; operation not repeated",
            acknowledge_interruption=True,
        )
        self.assertEqual(2, resumed["steps"])
        self.assertEqual(0, backend.calls)

    def test_completed_run_is_idempotent(self):
        state = self.run_backend(DemoBackend())
        resumed = Engine(self.agent, self.workspace, DemoBackend()).run(
            "", run_dir=self.agent / ".runs" / state["run_id"]
        )
        self.assertEqual(state, resumed)

    def test_missing_resume_path_does_not_start_empty_task(self):
        missing = self.agent / ".runs" / "typo"
        with self.assertRaises(ContractError):
            Engine(self.agent, self.workspace, DemoBackend()).run(
                "", run_dir=missing, feedback="Resume"
            )
        self.assertFalse(missing.exists())

    def test_resume_invalidates_review_before_pause(self):
        choices = [decision(), decision(role="reviewer"), decision("blocked", "")]
        state = self.run_backend(SequenceBackend(choices, [report(), report()]))
        self.assertTrue(state["reviewed"])
        resumed = Engine(
            self.agent, self.workspace, SequenceBackend([decision("finish", "")])
        ).run(
            "",
            run_dir=self.agent / ".runs" / state["run_id"],
            feedback="Workspace inspected after pause",
        )
        self.assertEqual("blocked", resumed["status"])
        self.assertIn("subsequent review", resumed["history"][-1]["completion_rejected"])

    def test_call_gets_remaining_wall_time_budget(self):
        self.change_limits(max_seconds=1, call_timeout=10)
        backend = SequenceBackend([decision("blocked", "")])
        with patch("agentkit.engine.time.monotonic", side_effect=[100.0] + [100.25] * 100), \
             patch.object(backend, "decide", wraps=backend.decide) as call:
            self.run_backend(backend)
            call.assert_called_once()
            self.assertAlmostEqual(call.call_args.args[1], 0.75)

    def test_elapsed_budget_survives_resume(self):
        state = self.run_backend(SequenceBackend([decision("blocked", "")]))
        folder = self.agent / ".runs" / state["run_id"]
        state["elapsed_seconds"] = 9999
        save(folder / "state.json", state)
        resumed = Engine(self.agent, self.workspace, SequenceBackend([])).run(
            "", run_dir=folder, feedback="Attempt resume without resetting time"
        )
        self.assertEqual("blocked", resumed["status"])
        self.assertIn("Wall-time budget", resumed["summary"])

    def test_resume_cannot_cross_company(self):
        state = self.run_backend(SequenceBackend([decision("blocked", "")]))
        cfg = read_json(self.agent / "agent.json")
        cfg["company"] = "Another company"
        save(self.agent / "agent.json", cfg)
        with self.assertRaises(ContractError):
            Engine(self.agent, self.workspace, SequenceBackend([])).run(
                "", run_dir=self.agent / ".runs" / state["run_id"], feedback="x"
            )

    def test_workspace_lock_blocks_second_owner(self):
        with lock(self.workspace / ".agentkit.lock"):
            with self.assertRaises(RuntimeError):
                self.run_backend(DemoBackend())

    def test_skill_bundle_can_be_added_without_python_import(self):
        source = self.root / "example-skill"
        source.mkdir()
        (source / "SKILL.md").write_text(
            "---\nname: example-skill\ndescription: Example task guidance.\n---\nDo the assigned example.\n"
        )
        (source / "skill.py").write_text("raise RuntimeError('must not execute')")
        add_skill(self.agent, source, "developer")
        self.assertIn("example-skill", Catalog(self.agent).roles["developer"]["skills"])

    def test_malformed_frontmatter_and_yaml_objects_are_rejected(self):
        path = self.root / "bad-skill" / "SKILL.md"
        path.parent.mkdir()
        for text in [
            "missing",
            "---\nname: bad-skill\n---\nBody",
            "---\n!!python/object:os.PathLike {}\n---\nBody",
        ]:
            path.write_text(text)
            with self.assertRaises(ContractError):
                skill_metadata(path)

    def test_vendor_skill_matches_pinned_hash_and_includes_license(self):
        folder = LIBRARY / "skills/verification-before-completion"
        source = read_json(folder / "UPSTREAM.json")
        self.assertEqual(
            source["sha256"],
            hashlib.sha256((folder / "SKILL.md").read_bytes()).hexdigest(),
        )
        self.assertIn("MIT License", (folder / "LICENSE").read_text())

    def test_paperclip_company_and_owner_boundaries(self):
        issue = {
            "id": "i1",
            "title": "Fix",
            "companyId": "c1",
            "assigneeAgentId": "a1",
            "status": "todo",
        }
        self.assertIn("Fix", issue_to_task(issue, company_id="c1", agent_id="a1"))
        for company, agent in [("c2", "a1"), ("c1", "a2")]:
            with self.assertRaises(ContractError):
                issue_to_task(issue, company_id=company, agent_id=agent)
        self.assertEqual(
            "blocked",
            result_to_update({"status": "blocked", "run_id": "r", "summary": "x"})[
                "status"
            ],
        )

    def test_native_prompt_uses_explicit_portable_skill_paths(self):
        text = native_prompt(self.agent, "Research the current repository")
        self.assertIn("dynamic-workflow/SKILL.md", text.replace("\\", "/"))
        self.assertIn("Python engine is not running", text)

    def test_deepseek_backend_requires_local_api_key(self):
        with self.assertRaises(ContractError):
            DeepSeekBackend(api_key="")._call("{}", "decision", {}, 5)

    def test_deepseek_prompts_do_not_disclose_the_host_workspace_path(self):
        backend = DeepSeekBackend(api_key="test-only-key")
        context = {
            "workspace": str(self.workspace),
            "history": [{"artifact": str(self.workspace / "private.txt")}],
            "request_approval": lambda *_: None,
        }
        with patch.object(backend, "_call", return_value=decision()) as call:
            backend.decide(context, 5)
        planner_prompt = call.call_args.args[0]
        self.assertNotIn(str(self.workspace), planner_prompt)
        self.assertIn("<assigned-workspace>", planner_prompt)
        self.assertNotIn("request_approval", planner_prompt)

        with patch.object(backend, "_call", return_value=report()) as call:
            backend.execute(decision(), context, 5)
        worker_prompt = call.call_args.args[0]
        self.assertNotIn(str(self.workspace), worker_prompt)
        self.assertIn("<assigned-workspace>", worker_prompt)

    def test_deepseek_backend_rejects_unsafe_provider_urls(self):
        for base_url in (
            "http://api.deepseek.com",
            "file:///tmp/provider",
            "https://user:secret@api.deepseek.com",
            "https://api.deepseek.com?redirect=https://evil.example",
            "https://api.deepseek.com?",
            "https://api.deepseek.com/#fragment",
            "https://api.deepseek.com#",
            "https://[::1",
        ):
            with self.subTest(base_url=base_url), self.assertRaises(ContractError):
                DeepSeekBackend(api_key="test-only-key", base_url=base_url)

        backend = DeepSeekBackend(
            api_key="test-only-key", base_url="https://provider.example/v1/"
        )
        self.assertEqual("https://provider.example/v1", backend.base_url)

    def test_deepseek_backend_rejects_redirects_before_forwarding_credentials(self):
        class Response:
            closed = False

            def close(self):
                self.closed = True

        response = Response()
        with self.assertRaisesRegex(ContractError, "redirects are not allowed"):
            _NoProviderRedirect().redirect_request(
                None, response, 302, "Found", {}, "https://evil.example/collect"
            )
        self.assertTrue(response.closed)

    def test_deepseek_backend_parses_structured_response_without_persisting_key(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, limit):
                return json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {
                                            "action": "blocked",
                                            "role": "",
                                            "skills": [],
                                            "task": "Missing evidence",
                                            "reason": "The test fixture is intentionally blocked.",
                                        }
                                    )
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        class Opener:
            def open(self, request, timeout):
                self.request = request
                self.timeout = timeout
                return Response()

        opener = Opener()
        with patch(
            "agentkit.backends.urllib.request.build_opener", return_value=opener
        ) as build_opener:
            result = DeepSeekBackend(api_key="test-only-key")._call(
                "Return a blocked decision as JSON.", "decision", {}, 5
            )

        self.assertEqual("blocked", result["action"])
        request = opener.request
        self.assertIsInstance(build_opener.call_args.args[0], _NoProviderRedirect)
        self.assertEqual("Bearer test-only-key", request.get_header("Authorization"))
        self.assertIn("response_format", request.data.decode("utf-8"))

    def test_deepseek_backend_accepts_json_markdown_wrapper(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, limit):
                return json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": "```json\n"
                                    + json.dumps(
                                        {
                                            "action": "blocked",
                                            "role": "",
                                            "skills": [],
                                            "task": "Wrapped response",
                                            "reason": "The wrapper is tolerated.",
                                        }
                                    )
                                    + "\n```"
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        class Opener:
            def open(self, request, timeout):
                return Response()

        with patch("agentkit.backends.urllib.request.build_opener", return_value=Opener()):
            result = DeepSeekBackend(api_key="test-only-key")._call(
                "Return a blocked decision as JSON.", "decision", {}, 5
            )

        self.assertEqual("blocked", result["action"])

    def test_deepseek_backend_parses_wrapped_tool_arguments(self):
        self.assertEqual(
            {"path": "README.md"},
            DeepSeekBackend._parse_structured_content('```json\n{"path": "README.md"}\n```'),
        )

    def test_deepseek_backend_accepts_python_literal_tool_arguments(self):
        self.assertEqual(
            {"path": "README.md"},
            DeepSeekBackend._parse_tool_arguments("{'path': 'README.md'}"),
        )

    def test_deepseek_workspace_reader_falls_back_to_cp1252(self):
        path = self.workspace / "legacy.txt"
        path.write_bytes("Prüfung: Maßnahme".encode("cp1252"))
        result = DeepSeekBackend(api_key="test-only-key")._run_tool(
            "read_file", {"path": "legacy.txt"}, {"workspace": str(self.workspace)}, 5
        )
        self.assertEqual("Prüfung: Maßnahme", result)

    def test_deepseek_edit_file_requires_one_exact_match(self):
        path = self.workspace / "target.txt"
        path.write_text("alpha\nbeta\n", encoding="utf-8")
        result = DeepSeekBackend(api_key="test-only-key")._run_tool(
            "edit_file",
            {"path": "target.txt", "old_text": "beta", "new_text": "gamma"},
            {"workspace": str(self.workspace), "sandbox": "workspace-write"},
            5,
        )
        self.assertIn('"edited": "target.txt"', result)
        self.assertEqual("alpha\ngamma\n", path.read_text(encoding="utf-8"))

    def test_edit_preserves_crlf_and_rejects_ambiguous_matches(self):
        path = self.workspace / "target.txt"
        backend = DeepSeekBackend(api_key="test-only-key")
        context = {"workspace": str(self.workspace), "sandbox": "workspace-write"}
        path.write_bytes(b"alpha\r\nbeta\r\n")
        result = backend._run_tool("edit_file", {
            "path": "target.txt", "old_text": "alpha\nbeta\n", "new_text": "alpha\ngamma\n"
        }, context, 5)
        self.assertIn('"edited"', result)
        self.assertEqual(b"alpha\r\ngamma\r\n", path.read_bytes())
        original = b"beta\r\nbeta\r\n"
        path.write_bytes(original)
        result = backend._run_tool("edit_file", {
            "path": "target.txt", "old_text": "beta\n", "new_text": "gamma\n"
        }, context, 5)
        self.assertIn("edit_requires_one_match", result)
        self.assertEqual(original, path.read_bytes())

    def test_mixed_newline_edit_recovers_with_single_line_span(self):
        path = self.workspace / "target.py"
        original = b"def value():\n    return 1\r\n"
        path.write_bytes(original)
        backend = DeepSeekBackend(api_key="test-only-key")
        context = {"workspace": str(self.workspace), "sandbox": "workspace-write"}
        result = backend._run_tool("edit_file", {
            "path": "target.py", "old_text": "def value():\n    return 1\n",
            "new_text": "def value():\n    return 2\n",
        }, context, 5)
        self.assertIn("preferably without newlines", result)
        self.assertEqual(original, path.read_bytes())
        result = backend._run_tool("edit_file", {
            "path": "target.py", "old_text": "return 1", "new_text": "return 2",
        }, context, 5)
        self.assertIn('"edited"', result)
        self.assertEqual(b"def value():\n    return 2\r\n", path.read_bytes())

    def test_deepseek_refuses_large_existing_file_rewrite(self):
        path = self.workspace / "large.py"
        path.write_text("x" * 2_000, encoding="utf-8")
        result = DeepSeekBackend(api_key="test-only-key")._run_tool(
            "write_file",
            {"path": "large.py", "content": "short"},
            {"workspace": str(self.workspace), "sandbox": "workspace-write"},
            5,
        )
        self.assertIn("refusing_large_file_rewrite", result)
        self.assertEqual(2_000, path.stat().st_size)

    def test_deepseek_pytest_prefers_workspace_src(self):
        source_root = self.workspace / "src"
        source_root.mkdir()
        test_path = self.workspace / "tests" / "test_smoke.py"
        test_path.parent.mkdir()
        test_path.write_text("def test_ok(): pass\n", encoding="utf-8")
        completed = (0, "1 passed", "")
        with patch("agentkit.backends._process_result", return_value=completed) as run:
            DeepSeekBackend(api_key="test-only-key")._run_tool(
                "run_pytest",
                {"path": "tests/test_smoke.py"},
                {"workspace": str(self.workspace), "sandbox": "workspace-write"},
                5,
            )
        env = run.call_args.kwargs["env"]
        self.assertEqual("1", env["PYTHONDONTWRITEBYTECODE"])
        self.assertEqual(
            ["-p", "no:cacheprovider", "--", str(test_path.resolve())],
            run.call_args.args[0][-4:],
        )
        self.assertEqual(
            source_root.resolve(), Path(env["PYTHONPATH"].split(os.pathsep)[0]).resolve()
        )

    def test_pytest_subprocess_does_not_inherit_server_secrets(self):
        path = self.workspace / "test_environment.py"
        path.write_text(
            "import os\ndef test_environment():\n"
            "    assert 'DEEPSEEK_API_KEY' not in os.environ\n"
            "    assert 'UNRELATED_PRIVATE_TOKEN' not in os.environ\n"
            "    assert 'OPENAI_API_KEY' not in os.environ\n", encoding="utf-8")
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "probe-secret", "UNRELATED_PRIVATE_TOKEN": "other-secret", "OPENAI_API_KEY": "openai-secret"}):
            result = json.loads(DeepSeekBackend(api_key="probe-secret")._run_tool(
                "run_pytest", {"path": path.name},
                {"workspace": str(self.workspace), "sandbox": "workspace-write"}, 15))
        self.assertEqual(0, result["exit_code"], result)

    def test_resume_rejects_external_directory_and_mismatched_identity(self):
        state = self.run_backend(DemoBackend())
        external = self.root / "external"
        external.mkdir()
        save(external / "state.json", state)
        engine = Engine(self.agent, self.workspace, DemoBackend())
        with self.assertRaises(ContractError):
            engine.run("", run_dir=external, feedback="resume")
        folder = self.agent / ".runs" / state["run_id"]
        state["run_id"] = "0" * 32
        save(folder / "state.json", state)
        with self.assertRaises(ContractError):
            engine.run("", run_dir=folder, feedback="resume")

    def test_codex_adapter_uses_schema_stdin_and_role_sandbox(self):
        with patch("agentkit.backends.codex_command", return_value=["codex"]), patch(
            "agentkit.backends._windows_sandbox_selection", return_value="unelevated"
        ):
            backend = CodexBackend()
        ctx = {"workspace": str(self.workspace), "sandbox": "read-only"}

        def fake_run(args, prompt, cwd, timeout):
            self.assertEqual("-", args[-1])
            self.assertEqual("read-only", args[args.index("--sandbox") + 1])
            self.assertIn("--output-schema", args)
            Path(args[args.index("--output-last-message") + 1]).write_text(
                json.dumps(report()), encoding="utf-8"
            )
            return ""

        with patch("agentkit.backends.run_process", side_effect=fake_run):
            self.assertEqual(
                "success", backend._call("Task", "report", ctx, 5)["status"]
            )

    def test_process_timeout_and_nonzero_exit(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run_process(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                "",
                self.workspace,
                0.1,
            )
        with self.assertRaises(RuntimeError):
            run_process(
                [sys.executable, "-c", "raise SystemExit(7)"], "", self.workspace, 5
            )

    def test_process_output_is_bounded_while_subprocess_runs(self):
        command = (
            "import sys; "
            "sys.stdout.buffer.write(b'x' * 2100000); sys.stdout.buffer.flush()"
        )
        with self.assertRaisesRegex(ContractError, "capture limit"):
            run_process([sys.executable, "-c", command], "", self.workspace, 5)

    def test_readonly_deepseek_tools_cannot_modify_or_execute_workspace(self):
        backend = DeepSeekBackend(api_key="test-only-key")
        target = self.workspace / "target.txt"
        target.write_text("original")
        for sandbox in (None, "read-only"):
            for name in ("write_file", "edit_file", "run_pytest"):
                with self.subTest(sandbox=sandbox, tool=name), self.assertRaises(ContractError):
                    backend._run_tool(name, {"path": "target.txt", "content": "changed", "old_text": "original", "new_text": "changed"}, {"workspace": str(self.workspace), "sandbox": sandbox}, 5)
        self.assertEqual("original", target.read_text())
        self.assertEqual({"read_file", "list_files"}, {s["function"]["name"] for s in backend._tool_specs()})

    def test_deepseek_batch_cannot_exceed_tool_budget(self):
        backend = DeepSeekBackend(api_key="test-only-key")
        backend.max_tool_calls = 1
        calls = [{"id": str(i), "function": {"name": "list_files", "arguments": "{}"}} for i in range(2)]
        with patch.object(backend, "_chat", return_value={"tool_calls": calls}), patch.object(backend, "_run_tool", return_value="[]") as run:
            with self.assertRaisesRegex(ContractError, "limit exhausted"):
                backend._call("Task", "report", {"workspace": str(self.workspace)}, 5)
        self.assertEqual(1, run.call_count)

    def test_deepseek_expired_tool_cannot_write(self):
        with self.assertRaisesRegex(ContractError, "deadline"):
            DeepSeekBackend(api_key="test-only-key")._run_tool("write_file", {"path": "late.txt", "content": "late"}, {"workspace": str(self.workspace), "sandbox": "workspace-write"}, 0)
        self.assertFalse((self.workspace / "late.txt").exists())

    def test_deepseek_test_process_preserves_timeout_and_isolates_path_argument(self):
        target = self.workspace / "--help"
        target.mkdir()
        with patch("agentkit.backends._process_result", return_value=(1, "failure", "details")) as run:
            result = DeepSeekBackend(api_key="test-only-key")._run_tool("run_pytest", {"path": "--help"}, {"workspace": str(self.workspace), "sandbox": "workspace-write"}, 0.25)
        self.assertEqual(0.25, run.call_args.args[3])
        self.assertEqual(
            ["-p", "no:cacheprovider", "--", str(target.resolve())],
            run.call_args.args[0][-4:],
        )
        self.assertEqual(1, json.loads(result)["exit_code"])

    def test_deepseek_cannot_overwrite_coordination_files(self):
        for path in (".agentkit.lock", ".runs/run/state.json", "nested/.lock",
                     ".git/config", ".GIT/hooks/post-checkout", ".pytest_cache/state",
                     "nested/__pycache__/payload.pyc"):
            with self.subTest(path=path), self.assertRaisesRegex(ContractError, "coordination"):
                DeepSeekBackend(api_key="test-only-key")._run_tool("write_file", {"path": path, "content": "bad"}, {"workspace": str(self.workspace), "sandbox": "workspace-write"}, 5)

    def test_deepseek_allows_safe_relative_path_under_internal_named_ancestor(self):
        workspace = self.root / ".runs" / "workspace"
        workspace.mkdir(parents=True)
        result = DeepSeekBackend(api_key="test-only-key")._run_tool(
            "write_file", {"path": "safe.txt", "content": "safe"},
            {"workspace": str(workspace), "sandbox": "workspace-write"}, 5,
        )
        self.assertIn('"written": "safe.txt"', result)
        self.assertEqual("safe", (workspace / "safe.txt").read_text())

    @unittest.skipUnless(os.name == "nt", "Windows path aliases only")
    def test_deepseek_rejects_windows_ads_and_reserved_device_paths(self):
        for path in ("safe.txt:stream", "NUL", "nested/COM1.txt", "trailing. "):
            with self.subTest(path=path), self.assertRaises(ContractError):
                DeepSeekBackend(api_key="test-only-key")._run_tool(
                    "write_file", {"path": path, "content": "bad"},
                    {"workspace": str(self.workspace), "sandbox": "workspace-write"}, 5)

    @unittest.skipUnless(os.name == "nt", "Windows 8.3 aliases only")
    def test_deepseek_rejects_short_aliases_for_internal_paths(self):
        import ctypes

        internal = self.workspace / ".git"
        internal.mkdir()
        (internal / "config").write_text("credential = secret", encoding="utf-8")
        buffer = ctypes.create_unicode_buffer(32_768)
        length = ctypes.windll.kernel32.GetShortPathNameW(
            str(internal), buffer, len(buffer)
        )
        if not length or length >= len(buffer):
            self.skipTest("Windows short names are unavailable")
        alias = Path(buffer.value).name
        if alias.casefold() == ".git":
            self.skipTest("8.3 alias generation is disabled on this volume")
        backend = DeepSeekBackend(api_key="test-only-key")
        context = {"workspace": str(self.workspace), "sandbox": "workspace-write"}
        for tool, arguments in (
            ("read_file", {"path": f"{alias}/config"}),
            ("list_files", {"path": alias}),
            ("write_file", {"path": f"{alias}/new", "content": "bad"}),
        ):
            with self.subTest(tool=tool), self.assertRaises(ContractError):
                backend._run_tool(tool, arguments, context, 5)

    @unittest.skipUnless(os.name == "nt", "Windows 8.3 aliases only")
    def test_action_replay_identity_canonicalizes_case_and_short_aliases(self):
        import ctypes

        directory = self.workspace / "Long Replay Directory"
        directory.mkdir()
        buffer = ctypes.create_unicode_buffer(32_768)
        length = ctypes.windll.kernel32.GetShortPathNameW(
            str(directory), buffer, len(buffer)
        )
        if not length or length >= len(buffer):
            self.skipTest("Windows short names are unavailable")
        alias = Path(buffer.value).name
        if alias.casefold() == directory.name.casefold():
            self.skipTest("8.3 alias generation is disabled on this volume")
        variants = (
            ("write_file", {"content": "x"}),
            ("edit_file", {"old_text": "a", "new_text": "b"}),
            ("run_pytest", {}),
        )
        for tool, extra in variants:
            long_arguments = {
                "path": f"{directory.name}/Result.PY", **extra,
            }
            alias_arguments = {"path": f"{alias}/RESULT.py", **extra}
            with self.subTest(tool=tool):
                self.assertNotEqual(
                    action_digest(tool, long_arguments),
                    action_digest(tool, alias_arguments),
                )
                self.assertEqual(
                    replay_action_digest(tool, long_arguments, self.workspace),
                    replay_action_digest(tool, alias_arguments, self.workspace),
                )

    def test_new_run_id_is_bound_and_cannot_overwrite_checkpoint(self):
        run_id = "a" * 32
        engine = Engine(self.agent, self.workspace, DemoBackend())
        state = engine.run("Demo", new_run_id=run_id)
        self.assertEqual(run_id, state["run_id"])
        self.assertTrue((self.agent / ".runs" / run_id / "state.json").is_file())
        with self.assertRaisesRegex(ContractError, "already has a checkpoint"):
            engine.run("Other task", new_run_id=run_id)
        for invalid in ("../outside", "g" * 32, "A" * 32):
            with self.assertRaises(ContractError):
                engine.run("Demo", new_run_id=invalid)


if __name__ == "__main__":
    unittest.main()
