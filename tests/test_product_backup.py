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
    pre = list(data.glob("aistudio.db.before-restore-*"))
    assert pre
    assert stat.S_IMODE(pre[0].stat().st_mode) == 0o600
    upload_pre = list(data.glob("uploads.before-restore-*"))
    assert upload_pre
    assert (data / "uploads" / "org1" / "note.txt").is_file()


def test_restore_keeps_only_three_preimages(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    dest = tmp_path / "backups"
    env = _env(data, db)
    env.pop("AISTUDIO_BACKUP_PASS", None)
    for i in range(5):
        _make_db(db, i)
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
        r2 = subprocess.run(
            [str(RESTORE), str(backup)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r2.returncode == 0, r2.stderr
    leftovers = list(data.glob("aistudio.db.before-restore-*"))
    assert len(leftovers) <= 3


def test_restore_refuses_live_pid(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    dest = tmp_path / "backups"
    env = _env(data, db)
    env.pop("AISTUDIO_BACKUP_PASS", None)
    env.pop("AISTUDIO_RESTORE_FORCE", None)
    _make_db(db, 7)
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
    _make_db(db, 99)
    (data / "aistudio.pid").write_text(str(os.getpid()), encoding="utf-8")
    denied = subprocess.run(
        [str(RESTORE), str(backup)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert denied.returncode != 0
    assert "läuft" in (denied.stderr or "")
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT x FROM t").fetchone()[0] == 99
    conn.close()
    env["AISTUDIO_RESTORE_FORCE"] = "1"
    forced = subprocess.run(
        [str(RESTORE), str(backup)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert forced.returncode == 0, forced.stderr
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT x FROM t").fetchone()[0] == 7
    conn.close()


def test_restore_ignores_stale_pid(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    dest = tmp_path / "backups"
    env = _env(data, db)
    env.pop("AISTUDIO_BACKUP_PASS", None)
    env.pop("AISTUDIO_RESTORE_FORCE", None)
    _make_db(db, 3)
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
    _make_db(db, 8)
    (data / "aistudio.pid").write_text("999999999\n", encoding="utf-8")
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
    assert conn.execute("SELECT x FROM t").fetchone()[0] == 3
    conn.close()


def test_housekeeping_prunes_restore_leftovers(tmp_path, monkeypatch):
    from product import config, housekeeping

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "aistudio.db")
    (tmp_path / "aistudio.db").write_bytes(b"live")
    for i in range(5):
        p = tmp_path / f"aistudio.db.before-restore-2020010{i}T000000Z"
        p.write_bytes(b"old")
        os.utime(p, (1_000_000 + i, 1_000_000 + i))
        d = tmp_path / f"uploads.before-restore-2020010{i}T000000Z"
        d.mkdir()
        (d / "secret.txt").write_text("tenant", encoding="utf-8")
        os.utime(d, (1_000_000 + i, 1_000_000 + i))
    out = housekeeping.prune_restore_leftovers()
    assert out["db"] == 2
    assert out["uploads"] == 2
    db_left = sorted(p.name for p in tmp_path.glob("aistudio.db.before-restore-*"))
    up_left = sorted(p.name for p in tmp_path.glob("uploads.before-restore-*"))
    assert len(db_left) == 3
    assert len(up_left) == 3
    assert (tmp_path / "aistudio.db").read_bytes() == b"live"
    newest_up = tmp_path / "uploads.before-restore-20200104T000000Z"
    assert (newest_up / "secret.txt").is_file()


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


def test_backup_script_drops_plaintext_if_encrypt_fails():
    text = BACKUP.read_text(encoding="utf-8")
    assert "Klartext nicht behalten" in text
    assert 'rm -f "$src" "$dest"' in text


def test_encrypted_backup_scrubs_plaintext_when_openssl_fails(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    _make_db(db, 7)
    note = data / "uploads" / "org1" / "note.txt"
    note.parent.mkdir(parents=True)
    note.write_text("must-not-linger", encoding="utf-8")
    dest = tmp_path / "backups"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "openssl"
    fake.write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
    os.chmod(fake, 0o755)
    env = _env(data, db)
    env["AISTUDIO_BACKUP_PASS"] = "unit-test-backup-pass"
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    r = subprocess.run(
        [str(BACKUP), str(dest)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode != 0
    assert "Klartext nicht behalten" in (r.stderr + r.stdout)
    leftovers = list(dest.glob("*")) if dest.is_dir() else []
    assert not any(p.name.endswith(".db") and not p.name.endswith(".enc") for p in leftovers)
    assert not any(p.name.endswith(".tar.gz") for p in leftovers)
    assert not any("SQLite" in p.read_bytes()[:32] for p in leftovers if p.is_file())


@pytest.mark.skipif(
    subprocess.call(["openssl", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0,
    reason="openssl missing",
)
def test_backup_reads_pass_from_data_backup_env(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    _make_db(db, 21)
    (data / "backup.env").write_text("AISTUDIO_BACKUP_PASS=file-only-backup-pass\n", encoding="utf-8")
    os.chmod(data / "backup.env", 0o600)
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
    assert backup.name.endswith(".enc")
    assert b"SQLite" not in backup.read_bytes()
    bak = data / "backup.env"
    hidden = data / "backup.env.hidden"
    bak.rename(hidden)
    denied_env = _env(data, db)
    denied_env.pop("AISTUDIO_BACKUP_PASS", None)
    denied = subprocess.run(
        [str(RESTORE), str(backup)],
        cwd=str(ROOT),
        env=denied_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert denied.returncode != 0
    hidden.rename(bak)
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
    assert conn.execute("SELECT x FROM t").fetchone()[0] == 21
    conn.close()


@pytest.mark.skipif(
    subprocess.call(["openssl", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0,
    reason="openssl missing",
)
def test_backup_inits_pass_in_production(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    _make_db(db, 3)
    dest = tmp_path / "backups"
    env = _env(data, db)
    env.pop("AISTUDIO_BACKUP_PASS", None)
    env["AISTUDIO_ENV"] = "production"
    r = subprocess.run(
        [str(BACKUP), str(dest)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "geschrieben" in (r.stderr or "")
    bakenv = data / "backup.env"
    assert bakenv.is_file()
    assert stat.S_IMODE(bakenv.stat().st_mode) == 0o600
    first = bakenv.read_text(encoding="utf-8")
    assert first.startswith("AISTUDIO_BACKUP_PASS=")
    backup = Path(r.stdout.strip())
    assert backup.name.endswith(".enc")
    assert b"SQLite" not in backup.read_bytes()
    r2 = subprocess.run(
        [str(BACKUP), str(dest)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 0, r2.stderr
    assert "geschrieben" not in (r2.stderr or "")
    assert bakenv.read_text(encoding="utf-8") == first
    _make_db(db, 99)
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
    assert conn.execute("SELECT x FROM t").fetchone()[0] == 3
    conn.close()


def test_install_appends_missing_backup_pass(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "install.sh").write_bytes((ROOT / "scripts" / "install.sh").read_bytes())
    os.chmod(scripts / "install.sh", 0o755)
    envf = tmp_path / ".env"
    envf.write_text("AISTUDIO_SECRET=keep-this-secret-value-xx\nAISTUDIO_ENV=production\n", encoding="utf-8")
    os.chmod(envf, 0o600)
    r = subprocess.run(
        [str(scripts / "install.sh")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    text = envf.read_text(encoding="utf-8")
    assert "AISTUDIO_SECRET=keep-this-secret-value-xx" in text
    assert "AISTUDIO_BACKUP_PASS=" not in text
    bakenv = tmp_path / "backup.env"
    assert bakenv.is_file()
    lines = [ln for ln in bakenv.read_text(encoding="utf-8").splitlines() if ln.startswith("AISTUDIO_BACKUP_PASS=")]
    assert len(lines) == 1
    assert len(lines[0].split("=", 1)[1].strip()) >= 20
    assert stat.S_IMODE(bakenv.stat().st_mode) == 0o600
    assert not (tmp_path / "data" / "backup.env").exists()
    assert "nachgetragen" in (r.stdout + r.stderr)
    assert "backup.env" in (r.stdout + r.stderr)
    assert "AISTUDIO_HOST=127.0.0.1" in text
    assert "AISTUDIO_ALLOWED_HOSTS=127.0.0.1,localhost" in text
    assert "AISTUDIO_TRUST_PROXY=true" in text
    assert "AISTUDIO_PROXY_IPS=127.0.0.1,::1" in text
    assert "AISTUDIO_SESSION_IDLE=14400" in text
    assert "AISTUDIO_LLM_EGRESS=in_boundary" in text
    metrics = [ln for ln in text.splitlines() if ln.startswith("AISTUDIO_METRICS_TOKEN=")]
    assert len(metrics) == 1
    assert len(metrics[0].split("=", 1)[1].strip()) >= 16
    assert "nachgetragen: AISTUDIO_HOST" in (r.stdout + r.stderr)
    assert "nachgetragen: AISTUDIO_ALLOWED_HOSTS" in (r.stdout + r.stderr)
    assert "nachgetragen: AISTUDIO_METRICS_TOKEN" in (r.stdout + r.stderr)


def test_install_moves_backup_pass_out_of_dotenv(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "install.sh").write_bytes((ROOT / "scripts" / "install.sh").read_bytes())
    os.chmod(scripts / "install.sh", 0o755)
    envf = tmp_path / ".env"
    envf.write_text(
        "AISTUDIO_SECRET=keep-this-secret-value-xx\n"
        "AISTUDIO_BACKUP_PASS=existing-backup-pass-value\n",
        encoding="utf-8",
    )
    os.chmod(envf, 0o600)
    r = subprocess.run(
        [str(scripts / "install.sh")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    text = envf.read_text(encoding="utf-8")
    assert "AISTUDIO_SECRET=keep-this-secret-value-xx" in text
    assert "AISTUDIO_BACKUP_PASS=" not in text
    bakenv = tmp_path / "backup.env"
    assert bakenv.read_text(encoding="utf-8").strip() == "AISTUDIO_BACKUP_PASS=existing-backup-pass-value"
    assert not (tmp_path / "data" / "backup.env").exists()
    assert "verschoben" in (r.stdout + r.stderr)


def test_install_migrates_legacy_data_backup_env(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "install.sh").write_bytes((ROOT / "scripts" / "install.sh").read_bytes())
    os.chmod(scripts / "install.sh", 0o755)
    envf = tmp_path / ".env"
    envf.write_text("AISTUDIO_SECRET=keep-this-secret-value-xx\n", encoding="utf-8")
    os.chmod(envf, 0o600)
    data = tmp_path / "data"
    data.mkdir()
    (data / "backup.env").write_text("AISTUDIO_BACKUP_PASS=legacy-data-backup-pass\n", encoding="utf-8")
    os.chmod(data / "backup.env", 0o600)
    r = subprocess.run(
        [str(scripts / "install.sh")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    bakenv = tmp_path / "backup.env"
    assert bakenv.read_text(encoding="utf-8").strip() == "AISTUDIO_BACKUP_PASS=legacy-data-backup-pass"
    assert not (data / "backup.env").exists()
    assert "verschoben" in (r.stdout + r.stderr)


@pytest.mark.skipif(
    subprocess.call(["openssl", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0,
    reason="openssl missing",
)
def test_backup_reads_pass_from_checkout_backup_env(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    _make_db(db, 17)
    (tmp_path / "backup.env").write_text("AISTUDIO_BACKUP_PASS=checkout-backup-pass-xx\n", encoding="utf-8")
    os.chmod(tmp_path / "backup.env", 0o600)
    dest = tmp_path / "backups"
    env = _env(data, db)
    env.pop("AISTUDIO_BACKUP_PASS", None)
    env["AISTUDIO_ROOT"] = str(tmp_path)
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
    assert b"SQLite" not in backup.read_bytes()


@pytest.mark.skipif(
    subprocess.call(["openssl", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0,
    reason="openssl missing",
)
def test_backup_reads_pass_from_backup_env_path(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "aistudio.db"
    _make_db(db, 19)
    secret = tmp_path / "secret" / "backup.env"
    secret.parent.mkdir()
    secret.write_text("AISTUDIO_BACKUP_PASS=dedicated-volume-backup-pass\n", encoding="utf-8")
    os.chmod(secret, 0o600)
    dest = tmp_path / "backups"
    env = _env(data, db)
    env.pop("AISTUDIO_BACKUP_PASS", None)
    env["AISTUDIO_BACKUP_ENV"] = str(secret)
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
    assert b"SQLite" not in backup.read_bytes()
    assert not (data / "backup.env").exists()


def test_compose_publishes_localhost_only():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "127.0.0.1:8123:8123" in text
    assert '"8123:8123"' not in text
    assert "init: true" in text
    assert "pids_limit: 128" in text
    assert "/tmp:size=64M" in text
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "sqlite3" in dockerfile
    assert "openssl" in dockerfile
    prod = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert 'profiles: ["backup"]' in prod
    assert "network_mode: none" in prod
    after = prod.split("backup:")[1]
    before = prod.split("backup:")[0]
    assert "init: true" in after
    assert "pids_limit: 32" in after
    assert "/tmp:size=64M" in after
    assert "AISTUDIO_SECRET:" not in after
    assert "AISTUDIO_BACKUP_PASS:" not in after
    assert "${AISTUDIO_METRICS_TOKEN:?" in before
    assert "AISTUDIO_BACKUP_ENV" in after
    assert "aistudio-backup-secret:/app/backup-secret" in after
    assert "aistudio-backup-secret:/app/backup-secret" not in before
    assert "target: /app/data/backup.env" in before
    assert "backup.env" in prod
    assert "8123" not in after
    assert "172.16.0.0/12" in prod
    assert "Gateway" in prod
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "backup.env" in ignore
    assert ".env" in ignore
    assert "bootstrap.env" in ignore
