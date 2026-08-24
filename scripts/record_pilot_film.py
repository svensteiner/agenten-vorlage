"""Record a silent client-ready film of the AI Studio guided demo.

Starts scripts/serve_pilot.py on 127.0.0.1 (PILOT_NO_BROWSER=1), drives the
real guided demo in a fresh Playwright Chromium context, writes a 1920x1080
WebM, and converts to MP4 when ffmpeg is available.

Usage:
    python scripts/record_pilot_film.py
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOST = "127.0.0.1"
READY_TIMEOUT_S = 15.0
POLL_INTERVAL_S = 0.05
DEMO_TIMEOUT_MS = 5 * 60 * 1000
STILLNESS_MS = 3000
VIEWPORT = {"width": 1920, "height": 1080}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVE_PILOT = PROJECT_ROOT / "scripts" / "serve_pilot.py"
OUT_DIR = PROJECT_ROOT / "pilot-assets" / "client-video"
MP4_NAME = "AI-Studio-Pilot-Muster-Bau.mp4"
WEBM_NAME = "AI-Studio-Pilot-Muster-Bau.webm"


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


def _stop_process(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    candidates = [
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ffmpeg" / "bin" / "ffmpeg.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
    ]
    for path in candidates:
        if path and path.is_file():
            return str(path)
    packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if packages.is_dir():
        hits = sorted(packages.glob("**/ffmpeg.exe"))
        if hits:
            return str(hits[0])
    return None


def _probe_duration(ffmpeg: str, media: Path) -> float | None:
    ffprobe = str(Path(ffmpeg).with_name("ffprobe.exe" if ffmpeg.lower().endswith(".exe") else "ffprobe"))
    cmd = None
    if Path(ffprobe).is_file():
        cmd = [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media),
        ]
    else:
        cmd = [
            ffmpeg,
            "-i",
            str(media),
            "-f",
            "null",
            "-",
        ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or "") + (result.stderr or "")
    for line in text.splitlines():
        line = line.strip()
        if line.replace(".", "", 1).isdigit():
            try:
                return float(line)
            except ValueError:
                continue
        if "Duration:" in line:
            # ffmpeg banner: Duration: 00:03:12.40, start: ...
            try:
                stamp = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
                h, m, s = stamp.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
            except (IndexError, ValueError):
                continue
    return None


def _convert_to_mp4(ffmpeg: str, webm: Path, mp4: Path) -> None:
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(webm),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        str(mp4),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not mp4.is_file() or mp4.stat().st_size <= 0:
        raise RuntimeError(
            "ffmpeg conversion failed "
            f"(exit {result.returncode}): {(result.stderr or result.stdout or '')[-2000:]}"
        )


def _record(base_url: str, raw_dir: Path) -> tuple[Path, str]:
    from playwright.sync_api import sync_playwright

    starter = "unknown"
    video_path: Path | None = None
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:
            raise RuntimeError(f"Chromium launch failed: {exc}") from exc
        context = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(raw_dir),
            record_video_size=VIEWPORT,
            locale="de-DE",
        )
        page = context.new_page()
        page.goto(base_url + "/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("#demoBtn", timeout=15000)
        # Give onboarding a moment to un-hide after init().
        page.wait_for_timeout(800)

        ob = page.locator("#obStart")
        if ob.is_visible():
            ob.click()
            starter = "onboarding #obStart"
        else:
            header = page.locator("#demoBtn")
            label = header.locator(".dl")
            if label.count() and "Geführte Demo" in (label.inner_text() or ""):
                header.click()
                starter = "header #demoBtn .dl"
            else:
                page.get_by_role("button", name="Geführte Demo").first.click()
                starter = "header button by accessible name"

        page.wait_for_function(
            """() => {
                const btn = document.querySelector('#demoBtn');
                if (!btn) return false;
                const label = (btn.querySelector('.dl') || {}).textContent || '';
                return btn.classList.contains('running') || /stoppen/i.test(label);
            }""",
            timeout=20000,
        )

        page.wait_for_function(
            """() => {
                const btn = document.querySelector('#demoBtn');
                if (!btn) return false;
                const label = (btn.querySelector('.dl') || {}).textContent || '';
                const running = btn.classList.contains('running');
                return !running && /Geführte Demo/i.test(label) && !/stoppen/i.test(label);
            }""",
            timeout=DEMO_TIMEOUT_MS,
        )
        page.wait_for_timeout(STILLNESS_MS)

        page.close()
        context.close()
        browser.close()

    videos = sorted(raw_dir.glob("*.webm"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not videos:
        raise RuntimeError(f"Playwright did not write a webm in {raw_dir}")
    video_path = videos[0]
    if video_path.stat().st_size <= 0:
        raise RuntimeError(f"Recorded video is empty: {video_path}")
    return video_path, starter


def _verify_pilot_active(base_url: str) -> None:
    with urllib.request.urlopen(base_url + "/pilot.config.js", timeout=5) as response:
        text = response.read().decode("utf-8")
    if "active: true" not in text.replace(" ", " "):
        # tolerate extra spaces; require the live switch
        import re

        if not re.search(r"(?m)^\s*active:\s*true\b", text):
            raise RuntimeError("pilot.config.js is not active:true — aborting film")
    if "Muster Bau" not in text:
        raise RuntimeError("pilot.config.js is not the Muster Bau path — aborting film")


def main() -> int:
    if not SERVE_PILOT.is_file():
        raise SystemExit(f"missing {SERVE_PILOT}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_dir = OUT_DIR / "_raw"
    if raw_dir.exists():
        for leftover in raw_dir.glob("*"):
            leftover.unlink()
    raw_dir.mkdir(parents=True, exist_ok=True)

    port = _unused_port()
    env = os.environ.copy()
    env["PILOT_NO_BROWSER"] = "1"
    process: subprocess.Popen[str] | None = None
    starter = "unknown"
    final_path: Path | None = None
    fmt = "webm"
    duration: float | None = None
    ffmpeg_note = "ffmpeg not found; kept WebM"

    try:
        process = subprocess.Popen(
            [sys.executable, str(SERVE_PILOT), str(port)],
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        base_url = f"http://{HOST}:{port}"
        _wait_until_serving(base_url, process)
        _verify_pilot_active(base_url)
        print(f"[record] serving {base_url} (Muster Bau, active:true)", flush=True)

        try:
            webm, starter = _record(base_url, raw_dir)
        except RuntimeError as exc:
            if "Chromium" in str(exc) or "BrowserType.launch" in str(exc) or "Executable doesn't exist" in str(exc):
                print("[record] Chromium missing — installing once and retrying", flush=True)
                install = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    cwd=str(PROJECT_ROOT),
                )
                if install.returncode != 0:
                    raise RuntimeError("playwright install chromium failed") from exc
                webm, starter = _record(base_url, raw_dir)
            else:
                raise

        dest_webm = OUT_DIR / WEBM_NAME
        if dest_webm.exists():
            dest_webm.unlink()
        shutil.move(str(webm), str(dest_webm))

        ffmpeg = _find_ffmpeg()
        if ffmpeg:
            dest_mp4 = OUT_DIR / MP4_NAME
            print(f"[record] converting with {ffmpeg}", flush=True)
            _convert_to_mp4(ffmpeg, dest_webm, dest_mp4)
            duration = _probe_duration(ffmpeg, dest_mp4) or _probe_duration(ffmpeg, dest_webm)
            dest_webm.unlink(missing_ok=True)
            final_path = dest_mp4
            fmt = "mp4"
            ffmpeg_note = f"converted with {ffmpeg}"
        else:
            final_path = dest_webm
            fmt = "webm"
            duration = None

        size = final_path.stat().st_size
        if size <= 0:
            raise RuntimeError(f"output is empty: {final_path}")

        print("=== PILOT FILM ===")
        print(f"path:      {final_path}")
        print(f"format:    {fmt}")
        print(f"size:      {size} bytes ({size / (1024 * 1024):.2f} MiB)")
        if duration is not None:
            print(f"duration:  {duration:.1f} s ({duration / 60:.2f} min)")
        else:
            print("duration:  unknown (no ffprobe/ffmpeg)")
        print(f"starter:   {starter}")
        print(f"ffmpeg:    {ffmpeg_note}")
        print("blocker:   none")
        return 0
    finally:
        _stop_process(process)
        try:
            if raw_dir.exists() and not any(raw_dir.iterdir()):
                raw_dir.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[record] interrupted", file=sys.stderr)
        raise SystemExit(130)
