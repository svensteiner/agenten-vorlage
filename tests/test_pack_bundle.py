"""Tests für core.packs.bundle — RESOLVE: content-address + signature integrity."""
import pytest

from core.packs.bundle import (
    BundleError,
    PackBundle,
    compute_content_hash,
    load_bundle,
    make_bundle,
    sign,
    verify_bundle,
)


class TestMakeBundle:
    def test_make_bundle_is_self_consistent(self):
        bundle = make_bundle(name="finance", version="1.2.0")
        # A freshly minted bundle verifies without error.
        assert verify_bundle(bundle) is bundle

    def test_content_hash_covers_sections(self):
        bundle = make_bundle(labels=("pii_class:health",))
        assert bundle.content_hash == compute_content_hash(bundle.sections())


class TestVerifyBundle:
    def test_tampered_sections_break_content_address(self):
        bundle = make_bundle(matrix_deltas={"confidential": "deny"})
        # Tamper with a section but keep the old hash/signature.
        tampered = PackBundle(
            name=bundle.name,
            version=bundle.version,
            ledger=bundle.ledger,
            matrix_deltas={"pii": "allow"},  # changed
            content_hash=bundle.content_hash,
            signature=bundle.signature,
        )
        with pytest.raises(BundleError):
            verify_bundle(tampered)

    def test_missing_content_hash_rejected(self):
        bundle = make_bundle()
        bare = PackBundle(name=bundle.name, version=bundle.version, ledger=bundle.ledger)
        with pytest.raises(BundleError):
            verify_bundle(bare)

    def test_wrong_signature_rejected(self):
        bundle = make_bundle()
        forged = PackBundle(
            name=bundle.name,
            version=bundle.version,
            ledger=bundle.ledger,
            content_hash=bundle.content_hash,
            signature="deadbeef",
        )
        with pytest.raises(BundleError):
            verify_bundle(forged)

    def test_unknown_publisher_key_rejected(self):
        bundle = make_bundle(key=b"attacker-key")
        with pytest.raises(BundleError):
            verify_bundle(bundle)  # verified against the real publisher key


class TestLoadBundle:
    def test_load_roundtrip_from_dict(self):
        bundle = make_bundle(name="hr", labels=("pii_class:employment",))
        data = {
            "name": bundle.name,
            "version": bundle.version,
            "ledger": bundle.ledger,
            "labels": list(bundle.labels),
            "content_hash": bundle.content_hash,
            "signature": bundle.signature,
        }
        loaded = load_bundle(data)
        assert loaded.name == "hr"
        assert loaded.labels == ("pii_class:employment",)

    def test_load_rejects_tampered_dict(self):
        bundle = make_bundle()
        data = {
            "name": "evil",  # does not match the signed hash
            "version": bundle.version,
            "ledger": bundle.ledger,
            "content_hash": bundle.content_hash,
            "signature": bundle.signature,
        }
        with pytest.raises(BundleError):
            load_bundle(data)

    def test_sign_is_deterministic(self):
        assert sign("abc") == sign("abc")
