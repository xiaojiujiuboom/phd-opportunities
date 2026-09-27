"""Orchestrator: runs all source adapters and writes ../data/jobs.json.

Usage: python scraper/fetch.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from classify import classify_job
from eligibility import filter_phds

# Source modules inspect JOB_KIND at import time. This project publishes PhDs only.
if os.getenv("JOB_KIND", "phd").lower() != "phd":
    raise SystemExit("Only JOB_KIND=phd is supported; no postdoc output will be written.")
from sources import ALL_SOURCES

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
OUT = Path(__file__).resolve().parent.parent / "data" / "jobs.json"


def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def main() -> int:
    session = _make_session()
    all_jobs: list[dict] = []
    successful_sources = 0
    for mod in ALL_SOURCES:
        name = getattr(mod, "SOURCE_ID", mod.__name__)
        try:
            jobs = mod.fetch(session)
        except Exception as e:
            print(f"[{name}] FAILED: {e}", file=sys.stderr)
            continue
        print(f"[{name}] {len(jobs)} jobs")
        successful_sources += 1
        for j in jobs:
            classify_job(j)
        all_jobs.extend(jobs)

    if not successful_sources or not all_jobs:
        print("No usable source records; keeping the previous snapshot.", file=sys.stderr)
        return 1
    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for job in all_jobs:
        job["last_seen"] = observed_at
    all_jobs, removed = filter_phds(all_jobs, observed_at=observed_at)
    out = {
        "updated_at": observed_at,
        "removed_by_reason": removed,
        "total": len(all_jobs),
        "jobs": all_jobs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(OUT)
    print(f"\nWrote {len(all_jobs)} jobs -> {OUT}")

    by_src: dict[str, int] = {}
    by_cc: dict[str, int] = {}
    for j in all_jobs:
        by_src[j.get("source", "?")] = by_src.get(j.get("source", "?"), 0) + 1
        by_cc[j.get("country", "?")] = by_cc.get(j.get("country", "?"), 0) + 1
    print("By source:", by_src)
    print("By country:", by_cc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
