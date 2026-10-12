from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from agentkit.catalog import Catalog
from agentkit.cli import main
from agentkit.contracts import ContractError, LIBRARY
from agentkit.scaffold import create


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(list(args))
        return result, stdout.getvalue(), stderr.getvalue()

    def test_profiles_and_compositions_share_generic_runtime(self):
        developer = create(self.root / "dev", "developer", "dev", "Example")
        bookkeeping = create(
            self.root / "books",
            "",
            "books",
            "Example",
            roles=["tax-advisor", "bmd-operator", "tax-reviewer"],
        )
        dev_config = json.loads((developer / "agent.json").read_text(encoding="utf-8"))
        book_config = json.loads(
            (bookkeeping / "agent.json").read_text(encoding="utf-8")
        )
        self.assertEqual(dev_config.keys(), book_config.keys())
        self.assertEqual("developer", dev_config["profile"])
        self.assertEqual("custom", book_config["profile"])
        self.assertTrue(book_config["require_review"])
        self.assertEqual(
            {"tax-advisor", "bmd-operator", "tax-reviewer"},
            set(Catalog(bookkeeping).roles),
        )
        self.assertTrue(
            (bookkeeping / ".agents/skills/dynamic-workflow/SKILL.md").is_file()
        )
        self.assertTrue(
            (bookkeeping / ".agents/skills/bookkeeping-review/SKILL.md").is_file()
        )

    def test_extra_builtin_skill_is_assigned_and_installed(self):
        pack = create(
            self.root / "pack",
            "research",
            "pack",
            "Example",
            extra_skills=[("researcher", "bookkeeping-review")],
        )
        catalog = Catalog(pack)
        self.assertIn("bookkeeping-review", catalog.roles["researcher"]["skills"])
        self.assertIn("bookkeeping-review", catalog.skills)

    def test_writable_custom_compositions_require_an_enabled_review_gate(self):
        for index, (roles, require_review) in enumerate(
            [
                (["developer"], None),
                (["developer", "reviewer"], False),
            ]
        ):
            with self.subTest(index=index):
                target = self.root / f"missing-review-{index}"
                with self.assertRaises(ContractError):
                    create(
                        target,
                        "",
                        "agent",
                        "Example",
                        roles=roles,
                        require_review=require_review,
                    )
                self.assertFalse(target.exists())

    def test_writable_profile_cannot_disable_review_gate(self):
        target = self.root / "unsafe-profile"
        with self.assertRaises(ContractError):
            create(
                target,
                "developer",
                "unsafe-profile",
                "Example",
                require_review=False,
            )
        self.assertFalse(target.exists())

    def test_read_only_custom_composition_can_omit_reviewer(self):
        pack = create(
            self.root / "read-only",
            "",
            "read-only",
            "Example",
            roles=["researcher"],
        )
        config = json.loads((pack / "agent.json").read_text(encoding="utf-8"))
        self.assertFalse(config["require_review"])

    def test_extra_skill_already_in_role_defaults_is_not_duplicated(self):
        pack = create(
            self.root / "pack",
            "",
            "pack",
            "Example",
            roles=["researcher"],
            extra_skills=[("researcher", "research-brief")],
        )
        self.assertEqual(
            1, Catalog(pack).roles["researcher"]["skills"].count("research-brief")
        )

    def test_invalid_compositions_are_atomic(self):
        cases = [
            ([], [], False),
            (["developer", "developer"], [], False),
            (["unknown"], [], False),
            (["developer"], [("missing", "research-brief")], False),
            (["developer"], [("developer", "missing")], False),
            (
                ["developer"],
                [("developer", "research-brief"), ("developer", "research-brief")],
                False,
            ),
            (["developer"], [], True),
        ]
        for index, (roles, extras, review) in enumerate(cases):
            with self.subTest(index=index):
                target = self.root / f"invalid-{index}"
                with self.assertRaises(ContractError):
                    create(
                        target,
                        "",
                        "agent",
                        "Example",
                        roles=roles,
                        extra_skills=extras,
                        require_review=review,
                    )
                self.assertFalse(target.exists())

    def test_malformed_composition_inputs_are_atomic(self):
        cases = [
            {"require_review": "false"},
            {"roles": ["researcher", 3]},
            {"roles": "researcher"},
            {"roles": ["researcher"], "extra_skills": [("researcher",)]},
            {"roles": ["researcher"], "extra_skills": [("researcher", 12)]},
            {
                "roles": ["researcher"],
                "extra_skills": "researcher:research-brief",
            },
        ]
        for index, kwargs in enumerate(cases):
            with self.subTest(index=index):
                target = self.root / f"malformed-{index}"
                with self.assertRaises(ContractError):
                    create(target, "", "agent", "Example", **kwargs)
                self.assertFalse(target.exists())

    def test_generation_failure_removes_partial_target(self):
        target = self.root / "partial"

        def fail_write(_path, _data):
            raise OSError("simulated write failure")

        with self.assertRaisesRegex(OSError, "simulated write failure"):
            create(
                target,
                "developer",
                "agent",
                "Example",
                storage_writer=fail_write,
            )
        self.assertFalse(target.exists())

    def test_cli_custom_roles_and_skill_flags(self):
        target = self.root / "cli-pack"
        result, output, error = self.run_cli(
            "init",
            str(target),
            "--role",
            "researcher",
            "--role",
            "tax-reviewer",
            "--skill",
            "researcher:bookkeeping-review",
            "--name",
            "cli-pack",
        )
        self.assertEqual(0, result, error)
        self.assertEqual(str(target), json.loads(output)["created"])
        config = json.loads((target / "agent.json").read_text(encoding="utf-8"))
        self.assertEqual("custom", config["profile"])
        self.assertIn("bookkeeping-review", config["roles"]["researcher"]["skills"])

    def test_cli_rejects_bad_composition_flags_atomically(self):
        cases = (
            ["--role", "researcher", "--profile", "research"],
            ["--skill", "not-a-pair"],
        )
        for index, flags in enumerate(cases):
            with self.subTest(index=index):
                target = self.root / f"bad-{index}"
                result, _output, _error = self.run_cli("init", str(target), *flags)
                self.assertEqual(1, result)
                self.assertFalse(target.exists())

    def test_cli_empty_explicit_profile_is_rejected(self):
        target = self.root / "empty-profile"
        result, _output, _error = self.run_cli(
            "init", str(target), "--profile", ""
        )
        self.assertEqual(1, result)
        self.assertFalse(target.exists())

    def test_profile_accepts_extra_skill_assignment(self):
        pack = create(
            self.root / "profile-plus-skill",
            "research",
            "research-pack",
            "Example",
            extra_skills=[("researcher", "bookkeeping-review")],
        )
        self.assertIn(
            "bookkeeping-review", Catalog(pack).roles["researcher"]["skills"]
        )

    def test_builtin_skill_catalog_is_the_runtime_catalog(self):
        self.assertTrue(
            (LIBRARY / "skills" / "bookkeeping-review" / "SKILL.md").is_file()
        )


if __name__ == "__main__":
    unittest.main()
