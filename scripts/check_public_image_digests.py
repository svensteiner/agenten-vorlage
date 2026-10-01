#!/usr/bin/env python3
"""Validate immutable image references used by the public Compose stack.

The default mode is deterministic and checks the deployment contract locally.
Pass ``--verify`` on a host with Docker Buildx to resolve each reference from
the registry before deployment.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path


_DIGEST = re.compile(r"^([^\s@]+)@sha256:([0-9a-f]{64})$")
_NAMES = (
    "AGENTKIT_APP_IMAGE",
    "AGENTKIT_OAUTH2_PROXY_IMAGE",
    "AGENTKIT_CADDY_IMAGE",
)


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise SystemExit(f"{path}:{number}: invalid environment assignment")
        values[key] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="deployment env file")
    parser.add_argument("--verify", action="store_true", help="ask Docker Buildx to resolve every image")
    args = parser.parse_args()
    values = _read_env(args.env_file) if args.env_file else dict(os.environ)
    images: list[str] = []
    for name in _NAMES:
        value = values.get(name, "").strip()
        match = _DIGEST.fullmatch(value)
        if not match or match.group(2) == "0" * 64 or "REPLACE_WITH" in value:
            raise SystemExit(f"{name} must be a non-placeholder image@sha256 digest")
        images.append(value)
    if args.verify:
        for image in images:
            subprocess.run(
                ["docker", "buildx", "imagetools", "inspect", image],
                check=True,
            )
    print(f"validated immutable digests for {len(images)} public images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
