from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVE_PILOT = PROJECT_ROOT / "scripts" / "serve_pilot.py"
HOST = "127.0.0.1"
READY_TIMEOUT_S = 10.0
POLL_INTERVAL_S = 0.05


def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


def _wait_until_serving(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_S
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = ""
            if process.stderr is not None:
                stderr = process.stderr.read()
            raise RuntimeError(
                "serve_pilot.py exited with "
                f"{process.returncode} before serving. {stderr}"
            )
        try:
            with urllib.request.urlopen(base_url + "/", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(
        f"Pilot server did not become ready at {base_url}: {last_error}"
    )


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


@pytest.fixture(scope="module")
def pilot_server():
    if not SERVE_PILOT.is_file():
        pytest.fail(f"missing {SERVE_PILOT}")
    port = _unused_port()
    env = os.environ.copy()
    env["PILOT_NO_BROWSER"] = "1"
    process = subprocess.Popen(
        [sys.executable, str(SERVE_PILOT), str(port)],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    base_url = f"http://{HOST}:{port}"
    try:
        _wait_until_serving(base_url, process)
        yield base_url
    finally:
        _stop_process(process)


def _get(base_url: str, path: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(base_url + path, timeout=5) as response:
        return response.status, response.read()


@pytest.mark.parametrize("path", ["/", "/pilot.config.js", "/data.js", "/app.js"])
def test_pilot_static_paths_return_200(pilot_server: str, path: str) -> None:
    status, body = _get(pilot_server, path)
    assert status == 200
    assert body


def test_pilot_config_is_active_muster_bau(pilot_server: str) -> None:
    status, body = _get(pilot_server, "/pilot.config.js")
    assert status == 200
    text = body.decode("utf-8")
    assert re.search(r"(?m)^\s*active:\s*true\b", text)
    assert "Muster Bau" in text


def test_app_js_defines_answer_card(pilot_server: str) -> None:
    status, body = _get(pilot_server, "/app.js")
    assert status == 200
    assert "function answerCard" in body.decode("utf-8")
