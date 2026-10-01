import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from cockpit.tenancy import (
    IdentityError,
    RuntimeLimitError,
    TenantRuntimeProvisioner,
)


class TenantRuntimeProvisionerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="agentkit-tenancy-"))
        self.data = self.tmp / "data"
        self.base = self.tmp / "base-agents"
        (self.base / "research").mkdir(parents=True)
        (self.base / "research" / "SOUL.md").write_text("research", encoding="utf-8")
        (self.base / "research" / "skills").mkdir()
        (self.base / "research" / "skills" / "guide.md").write_text("guide", encoding="utf-8")
        (self.base / "research" / ".runs").mkdir()
        (self.base / "research" / ".runs" / "private.json").write_text("secret", encoding="utf-8")
        (self.base / "research" / ".git").mkdir()
        (self.base / "research" / ".git" / "config").write_text("secret", encoding="utf-8")
        (self.base / "research" / "secret-state").mkdir()
        (self.base / "research" / "secret-state" / "token").write_text("secret", encoding="utf-8")
        (self.base / "research" / "Credentials").mkdir()
        (self.base / "research" / "Credentials" / "token").write_text("secret", encoding="utf-8")
        self.provisioner = TenantRuntimeProvisioner(self.data, self.base, identity_secret=b"test-secret-12345")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_provision_creates_scoped_paths_and_default_workspace(self):
        paths = self.provisioner.provision("Acme GmbH", "alice@example.com")

        self.assertTrue(paths.tenant_root.is_dir())
        self.assertTrue(paths.user_root.is_dir())
        self.assertTrue(paths.default_workspace.is_dir())
        self.assertTrue(paths.state_root.is_dir())
        self.assertEqual(paths.default_workspace, paths.workspaces_root / "default")
        self.assertNotIn("Acme GmbH", str(paths.tenant_root))
        self.assertNotIn("alice@example.com", str(paths.user_root))
        self.assertEqual(paths, self.provisioner.provision("Acme GmbH", "alice@example.com"))

    def test_identity_mapping_is_stable_opaque_and_namespaced(self):
        first = self.provisioner.provision("same", "same")
        second = self.provisioner.provision("same", "other")
        third = self.provisioner.provision("other", "same")

        self.assertRegex(first.tenant_id, r"^t_[0-9a-f]{32}$")
        self.assertRegex(first.user_id, r"^u_[0-9a-f]{32}$")
        self.assertNotEqual(second.user_id, first.user_id)
        self.assertNotEqual(third.tenant_id, first.tenant_id)
        self.assertNotEqual(first.tenant_id, first.user_id)

    def test_agent_snapshot_excludes_runtime_git_and_secret_state(self):
        paths = self.provisioner.provision("tenant", "user")
        pack = paths.agents_root / "research"

        self.assertEqual((pack / "SOUL.md").read_text(encoding="utf-8"), "research")
        self.assertEqual((pack / "skills" / "guide.md").read_text(encoding="utf-8"), "guide")
        self.assertFalse((pack / ".runs").exists())
        self.assertFalse((pack / ".git").exists())
        self.assertFalse((pack / "secret-state").exists())
        self.assertFalse((pack / "Credentials").exists())

        (self.base / "research" / "SOUL.md").write_text("changed", encoding="utf-8")
        self.assertEqual((pack / "SOUL.md").read_text(encoding="utf-8"), "research")

    def test_symlinked_base_content_is_rejected_and_never_copied(self):
        outside = self.tmp / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.base / "research" / "linked.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable on this host")

        with self.assertRaises(ValueError):
            self.provisioner.provision("tenant", "user")
        self.assertFalse((self.data / "tenants").exists() or (self.data / "tenant").exists())

    def test_ids_are_canonical_and_paths_cannot_escape(self):
        paths = self.provisioner.provision("tenant", "user")
        for bad in ("../other", "..", "a/b", "a\\b", "/absolute", "", "."):
            with self.subTest(bad=bad), self.assertRaises(IdentityError):
                self.provisioner.resolve_workspace(paths, bad)
            with self.subTest(agent=bad), self.assertRaises(IdentityError):
                self.provisioner.resolve_agent(paths, bad)

        workspace = self.provisioner.resolve_workspace(paths, "default")
        agent = self.provisioner.resolve_agent(paths, "research")
        self.assertEqual(workspace, paths.default_workspace)
        self.assertEqual(agent, paths.agents_root / "research")
        self.assertTrue(os.path.commonpath((str(paths.user_root), str(workspace))) == str(paths.user_root))

    def test_cross_tenant_and_user_paths_are_disjoint(self):
        a = self.provisioner.provision("tenant-a", "user")
        b = self.provisioner.provision("tenant-b", "user")
        c = self.provisioner.provision("tenant-a", "other-user")

        self.assertNotEqual(a.tenant_root, b.tenant_root)
        self.assertNotEqual(a.user_root, c.user_root)
        self.assertNotEqual(a.state_root, b.state_root)
        self.assertNotEqual(a.default_workspace, c.default_workspace)

    def test_factory_is_called_once_under_concurrency(self):
        calls = []
        lock = threading.Lock()

        def factory(paths):
            with lock:
                calls.append(paths)
            return object()

        results = []
        threads = [threading.Thread(target=lambda: results.append(self.provisioner.runtime("t", "u", factory))) for _ in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(calls), 1)
        self.assertEqual(len({id(value) for value in results}), 1)

    def test_runtime_limit_is_enforced(self):
        limited = TenantRuntimeProvisioner(self.data, self.base, identity_secret=b"test-secret-12345", max_cached_runtimes=1)
        limited.runtime("t", "u", lambda paths: paths)
        tenant_id, rejected_user_id = limited.identity_ids("t", "v")
        with self.assertRaises(RuntimeLimitError):
            limited.runtime("t", "v", lambda paths: paths)
        self.assertFalse((self.data / "tenants" / tenant_id / "users" / rejected_user_id).exists())

    def test_per_tenant_user_limit_is_enforced(self):
        limited = TenantRuntimeProvisioner(
            self.data, self.base, identity_secret=b"test-secret-12345", max_users_per_tenant=1
        )
        limited.runtime("t", "u", lambda paths: paths)
        tenant_id, rejected_user_id = limited.identity_ids("t", "v")
        with self.assertRaises(RuntimeLimitError):
            limited.runtime("t", "v", lambda paths: paths)
        self.assertFalse((self.data / "tenants" / tenant_id / "users" / rejected_user_id).exists())

    def test_identity_input_is_bounded(self):
        with self.assertRaises(IdentityError):
            self.provisioner.provision("", "user")
        with self.assertRaises(IdentityError):
            self.provisioner.provision("tenant", "x" * 257)


if __name__ == "__main__":
    unittest.main()
