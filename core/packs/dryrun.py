"""DRY-RUN — compute the install plan without committing (ADR-0017).

The dry-run produces the exact set of writes the COMMIT stage would perform, so
it can run in CI as a **release veto**: a pack whose install plan touches a
horizontal extension point (or whose validators fail) is caught before it ever
reaches a live store. It mutates nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from .bundle import PackBundle


@dataclass(frozen=True)
class InstallPlan:
    """The ordered set of section installs COMMIT would apply. Data, not effect."""

    pack: str
    version: str
    writes: tuple[tuple[str, str], ...] = ()  # (section, summary)

    def touched_sections(self) -> tuple[str, ...]:
        return tuple(section for section, _ in self.writes)


def plan_install(bundle: PackBundle) -> InstallPlan:
    writes: list[tuple[str, str]] = []
    if bundle.acl_fixtures:
        writes.append(("§1", f"{len(bundle.acl_fixtures)} ACL fixture(s) → conformance corpus"))
    if bundle.labels:
        writes.append(("§2", f"{len(bundle.labels)} label(s) → classification schema"))
    if bundle.matrix_deltas:
        writes.append(("§3", f"{len(bundle.matrix_deltas)} matrix delta(s) → label→action matrix"))
    if bundle.compliance_rows:
        writes.append(("§4", f"{len(bundle.compliance_rows)} compliance row(s) → compliance map"))
    if bundle.eval_models:
        writes.append(("§5", f"{len(bundle.eval_models)} eval model ref(s) → eval fixtures"))
    if bundle.agent_graph:
        writes.append(("§6", f"{len(bundle.agent_graph)} agent-graph edge(s) → handoff config"))
    return InstallPlan(pack=bundle.name, version=bundle.version, writes=tuple(writes))
