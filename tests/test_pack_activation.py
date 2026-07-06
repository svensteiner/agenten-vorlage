"""Tests für core.packs.activation — tenant scope, version pinning, fail-closed unload."""
import pytest

from core.packs.activation import ActivationRegistry, UnloadRefused


class TestActivation:
    def test_activate_is_tenant_scoped(self):
        reg = ActivationRegistry()
        reg.activate("tenant-a", "finance", "1.0.0")
        assert reg.is_active("tenant-a", "finance")
        assert not reg.is_active("tenant-b", "finance")  # scoped, no cross-tenant bleed

    def test_active_version_reported(self):
        reg = ActivationRegistry()
        reg.activate("t", "hr", "2.1.0")
        assert reg.active_version("t", "hr") == "2.1.0"


class TestPinning:
    def test_pin_changes_version(self):
        reg = ActivationRegistry()
        reg.activate("t", "hr", "2.1.0")
        reg.pin("t", "hr", "2.0.0")  # rollback to prior additive version
        assert reg.active_version("t", "hr") == "2.0.0"

    def test_pin_unknown_pack_raises(self):
        reg = ActivationRegistry()
        with pytest.raises(KeyError):
            reg.pin("t", "ghost", "1.0.0")


class TestFailClosedUnload:
    def test_unload_refused_while_label_live(self):
        reg = ActivationRegistry()
        reg.activate("t", "legal", "1.0.0", labels=("restricted:privileged",))
        reg.mark_label_live("t", "restricted:privileged")
        with pytest.raises(UnloadRefused):
            reg.unload("t", "legal")
        assert reg.is_active("t", "legal")  # still active — fail-closed

    def test_unload_succeeds_when_no_label_live(self):
        reg = ActivationRegistry()
        reg.activate("t", "legal", "1.0.0", labels=("restricted:privileged",))
        reg.unload("t", "legal")
        assert not reg.is_active("t", "legal")

    def test_unload_succeeds_after_label_cleared(self):
        reg = ActivationRegistry()
        reg.activate("t", "legal", "1.0.0", labels=("restricted:privileged",))
        reg.mark_label_live("t", "restricted:privileged")
        reg.clear_label("t", "restricted:privileged")
        reg.unload("t", "legal")  # no longer live → allowed
        assert not reg.is_active("t", "legal")

    def test_live_label_from_other_pack_does_not_block(self):
        reg = ActivationRegistry()
        reg.activate("t", "legal", "1.0.0", labels=("restricted:privileged",))
        reg.mark_label_live("t", "pii")  # unrelated label
        reg.unload("t", "legal")
        assert not reg.is_active("t", "legal")
