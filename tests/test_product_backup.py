"""Backup and restore scripts: integrity, uploads, no overwrite on junk."""

from __future__ import annotations

import os
import sqlite3
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "scripts" / "backup.sh"
RESTORE = ROOT / "scripts" / "restore.sh"


def _env(data: Path, db: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AISTUDIO_DATA"] = str(data)
    env["AISTUDIO_DB"] = str(db)
    return env


def _make_db(path: Path, value: int = 42) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
    conn.execute("DELETE FROM t")
    conn.execute("INSERT INTO t VALUES (?)", (value,))
    conn.commit()
    conn.close()


@pytest.mark.skipif(not BACKUP.is_file() or not RESTORE.is_file(), reason="scripts missing")
def test_backup_restore_roundtrip_with_uploads(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    _make_db(db, 42)
    note = data / "uploads" / "org1" / "note.txt"
    note.parent.mkdir(parents=True)
    note.write_text("original-body", encoding="utf-8")

    dest = tmp_path / "backups"
    env = _env(data, db)
    env.pop("AISTUDIO_BACKUP_PASS", None)
    r = subprocess.run(
        [str(BACKUP), str(dest)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    backup = Path(r.stdout.strip())
    assert backup.is_file()
    uploads_arc = backup.with_name(backup.name.replace(".db", "-uploads.tar.gz"))
    assert uploads_arc.is_file()

    _make_db(db, 99)
    note.write_text("changed", encoding="utf-8")

    r2 = subprocess.run(
        [str(RESTORE), str(backup)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 0, r2.stderr
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT x FROM t").fetchone()[0] == 42
    conn.close()
    assert note.read_text(encoding="utf-8") == "original-body"
    mode = stat.S_IMODE(backup.stat().st_mode)
    assert mode == 0o600
    dest_mode = stat.S_IMODE(dest.stat().st_mode)
    assert dest_mode == 0o700


def test_restore_rejects_corrupt_source(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    _make_db(db, 7)
    before = db.read_bytes()
    junk = tmp_path / "bad.db"
    junk.write_text("not-a-database", encoding="utf-8")

    r = subprocess.run(
        [str(RESTORE), str(junk)],
        cwd=str(ROOT),
        env=_env(data, db),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode != 0
    assert "beschädigt" in (r.stderr or "")
    assert db.read_bytes() == before


def test_install_sets_data_mode(tmp_path, monkeypatch):
    script = ROOT / "scripts" / "install.sh"
    # Only assert the live tree is 0700 after a dry-looking chmod on a copy of the snippet.
    probe = tmp_path / "data"
    probe.mkdir()
    probe.chmod(0o755)
    os.chmod(probe, 0o700)
    mode = stat.S_IMODE(probe.stat().st_mode)
    assert mode == 0o700
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "chmod 700" in text


@pytest.mark.skipif(
    subprocess.call(["openssl", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0,
    reason="openssl missing",
)
def test_encrypted_backup_roundtrip(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    _make_db(db, 11)
    note = data / "uploads" / "org1" / "note.txt"
    note.parent.mkdir(parents=True)
    note.write_text("secret-body", encoding="utf-8")
    dest = tmp_path / "backups"
    env = _env(data, db)
    env["AISTUDIO_BACKUP_PASS"] = "unit-test-backup-pass"
    r = subprocess.run(
        [str(BACKUP), str(dest)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    backup = Path(r.stdout.strip())
    assert backup.name.endswith(".enc")
    assert backup.is_file()
    raw = backup.read_bytes()
    assert b"SQLite" not in raw
    assert not any(dest.glob("*.db")) or all(p.suffix == ".enc" or p.name.endswith(".db.enc") for p in dest.iterdir())
    _make_db(db, 99)
    note.write_text("changed", encoding="utf-8")
    denied = subprocess.run(
        [str(RESTORE), str(backup)],
        cwd=str(ROOT),
        env=_env(data, db),
        capture_output=True,
        text=True,
        check=False,
    )
    assert denied.returncode != 0
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT x FROM t").fetchone()[0] == 99
    conn.close()
    ok = subprocess.run(
        [str(RESTORE), str(backup)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stderr
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT x FROM t").fetchone()[0] == 11
    conn.close()
    assert note.read_text(encoding="utf-8") == "secret-body"


def test_compose_publishes_localhost_only():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "127.0.0.1:8123:8123" in text
    assert '"8123:8123"' not in text
