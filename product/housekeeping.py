"""Expire sessions, drop old rows, checkpoint WAL, remove orphan uploads."""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from product import config, db

log = logging.getLogger("product.housekeeping")

_lock = threading.Lock()
_stop = threading.Event()
_thread: threading.Thread | None = None
_last: dict = {}


def _retention_days() -> int:
    raw = os.environ.get("AISTUDIO_AUDIT_RETENTION_DAYS", "365")
    try:
        days = int(raw)
    except ValueError:
        days = 365
    return max(30, min(days, 3650))


def _job_retention_days() -> int:
    raw = os.environ.get("AISTUDIO_JOB_RETENTION_DAYS", "90")
    try:
        days = int(raw)
    except ValueError:
        days = 90
    return max(7, min(days, 730))


def snapshot() -> dict:
    with _lock:
        return dict(_last)


def prune(conn=None) -> dict[str, int]:
    """Delete expired sessions and aged audit/job rows. Never logs row contents."""
    c = conn or db.get_conn()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    now_s = now.isoformat()
    audit_cut = (now - timedelta(days=_retention_days())).isoformat()
    job_cut = (now - timedelta(days=_job_retention_days())).isoformat()
    revoked_cut = (now - timedelta(days=7)).isoformat()

    sessions = c.execute(
        "DELETE FROM sessions WHERE expires_at < ? OR (revoked_at IS NOT NULL AND revoked_at < ?)",
        (now_s, revoked_cut),
    ).rowcount
    audit = c.execute(
        "DELETE FROM audit_log WHERE created_at < ?", (audit_cut,)
    ).rowcount
    stale = fail_stale_jobs(c)
    jobs = c.execute(
        "DELETE FROM jobs WHERE created_at < ?", (job_cut,)
    ).rowcount
    llm_cut = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    llm_rows = 0
    try:
        llm_rows = c.execute("DELETE FROM llm_usage WHERE day < ?", (llm_cut,)).rowcount
    except Exception:
        llm_rows = 0
    c.commit()
    log.info(
        "housekeeping sessions=%s audit=%s jobs=%s stale_jobs=%s llm_usage=%s",
        sessions,
        audit,
        jobs,
        stale,
        llm_rows,
    )
    return {
        "sessions": sessions,
        "audit": audit,
        "jobs": jobs,
        "stale_jobs": stale,
        "llm_usage": llm_rows,
    }


def fail_stale_jobs(conn=None, org_id: str | None = None) -> int:
    """Mark leftover 'running' jobs as error so a crash cannot block the org cap.

    Never writes task text. Live jobs newer than ``job_stale_seconds`` stay running.
    """
    c = conn or db.get_conn()
    cut = (
        datetime.now(timezone.utc) - timedelta(seconds=config.job_stale_seconds())
    ).replace(microsecond=0).isoformat()
    payload = json.dumps({"ok": False, "error": "stale"}, ensure_ascii=False)
    if org_id:
        cur = c.execute(
            "UPDATE jobs SET status = 'error', output_json = ? "
            "WHERE org_id = ? AND status = 'running' AND created_at < ?",
            (payload, org_id, cut),
        )
    else:
        cur = c.execute(
            "UPDATE jobs SET status = 'error', output_json = ? "
            "WHERE status = 'running' AND created_at < ?",
            (payload, cut),
        )
    n = int(cur.rowcount or 0)
    if n:
        c.commit()
        log.info("housekeeping stale_jobs=%s", n)
    return n


def wal_checkpoint(conn=None) -> dict[str, int]:
    """TRUNCATE WAL. Skip when backup/restore holds data/.backup.lock."""
    if config.backup_lock_busy():
        log.info("housekeeping wal skipped — backup lock held")
        return {"busy": 1, "log": 0, "checkpointed": 0, "skipped": 1}
    c = conn or db.get_conn()
    row = c.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    return {
        "busy": int(row[0] if row else 0),
        "log": int(row[1] if row and row[1] is not None else 0),
        "checkpointed": int(row[2] if row and row[2] is not None else 0),
    }


def prune_orphan_uploads(conn=None) -> int:
    """Remove leftover upload files whose document row is gone.

    Skip while backup/restore holds ``data/.backup.lock`` — ``backup.sh``
    tars ``uploads/`` under that lock.
    """
    if config.backup_lock_busy():
        log.info("housekeeping orphan_uploads skipped — backup lock held")
        return 0
    c = conn or db.get_conn()
    ids = {r["id"] for r in c.execute("SELECT id FROM documents").fetchall()}
    root = Path(config.DATA_DIR) / "uploads"
    if not root.is_dir():
        return 0
    try:
        root.resolve().relative_to(Path(config.DATA_DIR).resolve())
    except ValueError:
        return 0
    removed = 0
    for path in root.rglob("*.txt"):
        if not path.name.startswith("upload-"):
            continue
        if path.stem in ids:
            continue
        try:
            path.unlink()
            removed += 1
        except OSError:
            continue
    if removed:
        log.info("housekeeping orphan_uploads=%s", removed)
        config.clear_org_upload_bytes_cache()
    return removed


def _restore_keep() -> int:
    raw = os.environ.get("AISTUDIO_RESTORE_KEEP", "3")
    try:
        n = int(raw)
    except ValueError:
        n = 3
    return max(1, min(n, 14))


def prune_restore_leftovers() -> dict[str, int]:
    """Keep the newest N pre-restore copies; drop older DB files and upload trees.

    Never logs file contents. Paths must stay under the data dir or the DB parent.
    Skip while backup/restore holds ``data/.backup.lock``.
    """
    if config.backup_lock_busy():
        log.info("housekeeping restore_leftovers skipped — backup lock held")
        return {"db": 0, "uploads": 0, "skipped": 1}
    keep = _restore_keep()
    db_removed = 0
    upload_removed = 0
    db_path = Path(config.DB_PATH)
    parent = db_path.parent
    prefix = db_path.name + ".before-restore-"
    try:
        candidates = [
            p
            for p in parent.iterdir()
            if p.is_file() and p.name.startswith(prefix) and ".." not in p.name
        ]
    except OSError:
        candidates = []
    candidates.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    for path in candidates[keep:]:
        try:
            path.resolve().relative_to(parent.resolve())
            path.unlink()
            db_removed += 1
        except (OSError, ValueError):
            continue
    for path in candidates[:keep]:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    data = Path(config.DATA_DIR)
    try:
        dirs = [
            p
            for p in data.iterdir()
            if p.is_dir() and p.name.startswith("uploads.before-restore-") and ".." not in p.name
        ]
    except OSError:
        dirs = []
    dirs.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    for path in dirs[keep:]:
        try:
            path.resolve().relative_to(data.resolve())
            shutil.rmtree(path)
            upload_removed += 1
        except (OSError, ValueError):
            continue
    if db_removed or upload_removed:
        log.info("housekeeping restore_leftovers db=%s uploads=%s", db_removed, upload_removed)
    return {"db": db_removed, "uploads": upload_removed}


def run_once(conn=None) -> dict:
    """Startup/cron unit of work. Never logs tenant contents."""
    own = conn is None
    c = conn or db.connect()
    try:
        db.init_db(c)
        out: dict = prune(c)
        try:
            out["wal"] = wal_checkpoint(c)
        except Exception:
            log.exception("wal checkpoint skipped")
            out["wal"] = {}
        try:
            out["orphan_uploads"] = prune_orphan_uploads(c)
        except Exception:
            log.exception("orphan uploads skipped")
            out["orphan_uploads"] = 0
        try:
            out["restore_leftovers"] = prune_restore_leftovers()
        except Exception:
            log.exception("restore leftovers skipped")
            out["restore_leftovers"] = {"db": 0, "uploads": 0}
        config.harden_data_dir()
        try:
            if not (out.get("wal") or {}).get("skipped"):
                c.execute("PRAGMA optimize")
        except Exception:
            log.exception("pragma optimize skipped")
        with _lock:
            global _last
            _last = {
                "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "runs": int((_last or {}).get("runs") or 0) + 1,
                "sessions": out.get("sessions") or 0,
                "audit": out.get("audit") or 0,
                "jobs": out.get("jobs") or 0,
                "stale_jobs": out.get("stale_jobs") or 0,
                "orphan_uploads": out.get("orphan_uploads") or 0,
                "restore_leftovers": out.get("restore_leftovers") or {},
            }
        return out
    finally:
        if own:
            c.close()


def start_loop(interval_s: float | None = None) -> None:
    """Periodic prune while the process stays up. interval_s<=0 disables."""
    global _thread
    if interval_s is None:
        raw = os.environ.get("AISTUDIO_HOUSEKEEPING_HOURS", "24")
        try:
            hours = float(raw)
        except ValueError:
            hours = 24.0
        interval_s = max(0.0, hours) * 3600.0
    if interval_s <= 0:
        return
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()

    def _run() -> None:
        while not _stop.wait(interval_s):
            try:
                run_once()
            except Exception:
                log.exception("housekeeping loop skipped")

    _thread = threading.Thread(target=_run, name="aistudio-housekeeping", daemon=True)
    _thread.start()


def stop_loop() -> None:
    _stop.set()
    t = _thread
    if t is not None and t.is_alive():
        t.join(timeout=2)
