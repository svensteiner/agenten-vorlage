# Isolierte, hostgebundene Testausfuehrung

`--test-policy FILE` enables one host-configured test action for `run` and
`resume`. The exact JSON manifest is loaded by the host and its digest is bound
to the run and any pending approval. Supply the same manifest on resume. The
policy must be stored outside the project workspace.

The manifest is an exact version-1 object with `image_ref`, `image_id`,
`dependency_lock_sha256`, `docker_transport`, `test_files`, `support_files`,
`expected_test_count`, and `snapshot_paths` in addition to `version`. Each
listed test/support file has a SHA-256 digest. The image is digest-pinned and
its labels must identify the expected dependency lock. `docker_transport` is
host-selected as `native` or the fixed Ubuntu WSL adapter. The snapshot lists
all source needed by the suite, not just tests; no workspace discovery or
agent-selected test paths are performed.

The only exposed action is `run_isolated_tests` with an empty argument object.
It copies the manifest's explicit snapshot into a temporary staging directory,
verifies pinned bytes, then runs the complete pinned test list in a constrained
container with a read-only source mount, no network, fixed resource limits,
and bounded time/output. `run_pytest` and direct project execution are denied
when this policy is active. Every attempt is checkpointed before runner
dispatch; timeout or transport loss is not automatically replayed. A successful
test receipt is host-generated and bound to the run, policy, and workspace
fingerprint. Any write-capable worker step invalidates it. Completion requires
both a current passing receipt and a successful independent review.

This is defense in depth, not an operating-system sandbox guarantee. It assumes
the Docker daemon/transport and host are trusted and does not protect against
their compromise, a privileged concurrent workspace writer, or a malicious
in-process Python backend. The CLI/Python integration is local; the cockpit and
public hosting do not expose the host execution callback. Tests should be run
only with a curated manifest and an audited immutable image.
