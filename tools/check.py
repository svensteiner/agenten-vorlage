"""check.py — Manifest & config validation for the automation-agent template.

Validates that project/manifest.json, config.json, and referenced files are
consistent. Fails (exit 1) when a critical error is found. Adapted from the v3.0
validator to the core/ + project/ layout (JSON manifest + connectors.yaml).

Usage:
    python tools/check.py             # validate everything
    python tools/check.py --strict    # treat warnings as errors
    python tools/check.py --json      # machine-readable output (CI/CD)

Exit codes:
    0 = ok
    1 = errors found (or warnings in --strict)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "project"

KNOWN_TOOLS = {"file", "read", "grep", "glob", "web_search", "notify", "slack", "telegram"}
KNOWN_WORKER_TOOLS = {"file_read", "file_write", "file_list", "web_search", "notify"}
VALID_TRUST_LEVELS = {"low", "medium", "high"}
VALID_AUTONOMY = {"gated", "max"}


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def info(self, msg: str) -> None:
        self.infos.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "infos": self.infos,
        }


def _load_json(path: Path, result: CheckResult) -> dict[str, Any] | None:
    if not path.exists():
        result.error(f"{path.relative_to(ROOT)} fehlt.")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.error(f"{path.relative_to(ROOT)} ist kein gültiges JSON: {exc}")
        return None


def check_manifest(result: CheckResult) -> dict[str, Any] | None:
    manifest = _load_json(PROJECT / "manifest.json", result)
    if manifest is None:
        return None

    # Autonomy
    level = manifest.get("autonomy_level")
    if level is not None and level not in VALID_AUTONOMY:
        result.error(f"autonomy_level '{level}' ungültig (erlaubt: {sorted(VALID_AUTONOMY)}).")
    if level == "max":
        result.warn("autonomy_level ist 'max' — voll autonom, kein Freigabe-Gate (fail-open).")

    # Tool permissions
    perms = manifest.get("tool_permissions", {})
    for tool in perms.get("enabled", []):
        if tool not in KNOWN_TOOLS:
            result.warn(f"tool_permissions.enabled: unbekanntes Tool '{tool}'.")

    # Workers (least-privilege triad)
    workers = manifest.get("workers", {})
    writers = []
    for name, cfg in workers.items():
        trust = cfg.get("trust_level", "medium")
        if trust not in VALID_TRUST_LEVELS:
            result.error(f"Worker '{name}': trust_level '{trust}' ungültig.")
        for t in cfg.get("tools", []):
            if t not in KNOWN_WORKER_TOOLS:
                result.warn(f"Worker '{name}': unbekanntes Tool '{t}'.")
        if "file_write" in cfg.get("tools", []):
            writers.append(name)
    if len(writers) > 1:
        result.error(
            f"Leaf-Write verletzt: {len(writers)} Worker haben Schreibrecht ({writers}). "
            "Nur genau einer darf 'file_write' haben."
        )
    elif workers and not writers:
        result.info("Kein Worker mit Schreibrecht — rein lesender Agent.")

    # Handoffs allowlist must reference known workers (if any workers defined)
    allowlist = manifest.get("handoffs", {}).get("allowlist", [])
    if workers:
        for target in allowlist:
            if target not in workers:
                result.error(f"handoffs.allowlist: '{target}' ist kein definierter Worker.")

    # Skills referenced must exist on disk
    for skill in manifest.get("skills", []) or []:
        skill_dir = PROJECT / "skills" / str(skill)
        if not (skill_dir / "SKILL.md").exists():
            result.error(f"Skill '{skill}' referenziert, aber {skill_dir}/SKILL.md fehlt.")

    return manifest


def check_connectors(result: CheckResult) -> None:
    path = PROJECT / "connectors.yaml"
    if not path.exists():
        result.info("connectors.yaml fehlt — keine externen Quellen deklariert.")
        return
    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        data = yaml.safe_load(text) or {}
    except ImportError:
        result.info("PyYAML nicht installiert — connectors.yaml nur oberflächlich geprüft.")
        return
    for conn in data.get("connectors", []) or []:
        name = conn.get("name", "?")
        if not conn.get("url_env"):
            result.warn(f"Connector '{name}': kein 'url_env' — Secret sollte über eine Env-Variable kommen.")


def check_config(result: CheckResult) -> None:
    config = _load_json(ROOT / "config.json", result)
    if config is None:
        return
    manifest_level = None
    manifest_path = PROJECT / "manifest.json"
    if manifest_path.exists():
        try:
            manifest_level = json.loads(manifest_path.read_text(encoding="utf-8")).get("autonomy_level")
        except json.JSONDecodeError:
            pass
    if manifest_level and config.get("autonomy_level") and config["autonomy_level"] != manifest_level:
        result.error(
            f"autonomy_level uneinig: config.json='{config['autonomy_level']}' "
            f"vs manifest.json='{manifest_level}'. Über die Einstellungs-UI beheben."
        )


def run_checks() -> CheckResult:
    result = CheckResult()
    check_manifest(result)
    check_connectors(result)
    check_config(result)
    return result


def _print_human(result: CheckResult) -> None:
    for msg in result.errors:
        print(f"  [FEHLER] {msg}")
    for msg in result.warnings:
        print(f"  [WARN]  {msg}")
    for msg in result.infos:
        print(f"  [INFO]  {msg}")
    if result.ok and not result.warnings:
        print("  ✓ Alles in Ordnung.")
    print(f"\n{len(result.errors)} Fehler, {len(result.warnings)} Warnungen.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the agent project pack.")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    result = run_checks()
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_human(result)

    failed = not result.ok or (args.strict and bool(result.warnings))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
