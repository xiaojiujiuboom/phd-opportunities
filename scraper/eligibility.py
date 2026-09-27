"""Conservative PhD-only publication policy; R1 alone is not evidence."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

PHD_TITLE = re.compile(
    r"\bph\.?\s*d\.?\b|\bdoctoral\b|\bdoctorate\b|\bdoctorand\w*\b|"
    r"\bdoktorand\w*\b|\bpromovend\w*\b|\bdoctorant\w*\b|"
    r"\bdottorat\w*\b|\bstipendiat\w*\b", re.I,
)
OTHER_ROLE = re.compile(
    r"\bpost[-\s]?doc(?:toral)?\b|\bp[oó]s[-\s]?doutoral\b|"
    r"\bprofessor\b|\btechnician\b|\blaboratory manager\b", re.I,
)
CLOSED = {"closed", "expired", "withdrawn", "filled", "cancelled", "canceled"}
UNDATED_TTL_DAYS = 7


def parse_day(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def exclusion_reason(job: dict, *, today: date, observed_at: str | None) -> str | None:
    if str(job.get("status", "")).lower() in CLOSED:
        return "closed"
    title = str(job.get("title", ""))
    if OTHER_ROLE.search(title):
        return "mixed_or_non_phd_role"
    if not PHD_TITLE.search(title):
        return "phd_not_confirmed"
    raw_deadline = job.get("deadline")
    deadline = parse_day(raw_deadline)
    if raw_deadline and deadline is None:
        return "invalid_deadline"
    if deadline is not None:
        return "expired" if deadline < today else None
    observed = parse_day(job.get("last_verified") or job.get("last_seen") or observed_at)
    if observed is None or observed > today or today - observed > timedelta(days=UNDATED_TTL_DAYS):
        return "undated_stale"
    return None


def filter_phds(jobs: list[dict], *, today: date | None = None,
                observed_at: str | None = None) -> tuple[list[dict], dict[str, int]]:
    today = today or datetime.now().astimezone().date()
    kept, removed = [], {}
    for job in jobs:
        reason = exclusion_reason(job, today=today, observed_at=observed_at)
        if reason:
            removed[reason] = removed.get(reason, 0) + 1
            continue
        published = dict(job, opportunity_type="phd")
        # A missing deadline never means that the vacancy is confirmed open.
        published["status"] = "deadline_not_passed" if parse_day(job.get("deadline")) else "deadline_unspecified"
        kept.append(published)
    return kept, removed
