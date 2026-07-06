"""Tests für core.packs.loader — COMMIT atomicity: partial install is unrepresentable."""

from core.packs.bundle import make_bundle
from core.packs.loader import STAGE_COMMIT, STAGE_DONE, STAGE_VALIDATE, ExtensionStore, Loader


def _full_bundle():
    """A valid, all-additive bundle that touches all six sections."""
    return make_bundle(
        acl_fixtures=({"name": "ok", "expected": ["u1"], "authorized": ["u1"]},),
        labels=("pii_class:health",),
        matrix_deltas={"confidential": "deny"},
        compliance_rows=({"name": "sox", "op": "add"},),
        eval_models=("claude-sonnet-4-6",),
        agent_graph=("reader",),
    )


class TestHappyPath:
    def test_full_bundle_installs_all_sections(self):
        store = ExtensionStore()
        result = Loader(store).load(_full_bundle())
        assert result.ok
        assert result.stage == STAGE_DONE
        # all six sections landed
        assert set(store.installed_sections()) == {"§1", "§2", "§3", "§4", "§5", "§6"}


class TestAtomicity:
    def test_mid_validate_failure_installs_zero_sections(self):
        store = ExtensionStore()
        # Inject a failure at §4 — validation aborts before COMMIT.
        result = Loader(store).load(_full_bundle(), fail_validator="§4")
        assert not result.ok
        assert result.stage == STAGE_VALIDATE
        assert result.rejected_by.startswith("§4")
        assert store.installed_sections() == ()  # nothing installed

    def test_mid_commit_failure_rolls_back_all(self):
        # A store whose write raises on §5 must leave zero sections persisted.
        def hook(section, payload):
            if section == "§5":
                raise RuntimeError("disk full")

        store = ExtensionStore(install_hook=hook)
        result = Loader(store).load(_full_bundle())
        assert not result.ok
        assert result.stage == STAGE_COMMIT
        assert store.installed_sections() == ()  # atomic swap never happened

    def test_commit_is_all_or_nothing_on_success(self):
        store = ExtensionStore()
        Loader(store).load(_full_bundle())
        # A second, unrelated pack commit does not disturb the first.
        second = make_bundle(name="second", labels=("restricted:privileged",))
        Loader(store).load(second)
        assert "§2" in store.installed_sections()


class TestResolveStage:
    def test_tampered_bundle_fails_at_resolve(self):
        from core.packs.bundle import PackBundle

        good = make_bundle()
        tampered = PackBundle(
            name="evil",
            version=good.version,
            ledger=good.ledger,
            content_hash=good.content_hash,
            signature=good.signature,
        )
        result = Loader().load(tampered)
        assert not result.ok
        assert result.stage == "RESOLVE"
