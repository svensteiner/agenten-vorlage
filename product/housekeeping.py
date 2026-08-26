"""Expire sessions and drop old audit/job rows so production DBs stay bounded."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from product import db

log = logging.getLogger("product.housekeeping")


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
    jobs = c.execute(
        "DELETE FROM jobs WHERE created_at < ?", (job_cut,)
    ).rowcount
    c.commit()
    log.info("housekeeping sessions=%s audit=%s jobs=%s", sessions, audit, jobs)
    return {"sessions": sessions, "audit": audit, "jobs": jobs}
