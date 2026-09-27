"""Orchestrator: runs all source adapters and writes ../data/jobs.json.

Usage: python scraper/fetch.py
"""
from __future__ import annotations

import json
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import monotonic

import requests

from classify import classify_job
from eligibility import filter_phds
from bundle import bundle

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", help="Refresh one named adapter, preserving other sources")
    args = parser.parse_args()
    selected = [m for m in ALL_SOURCES if not args.source or m.SOURCE_ID in args.source]
    if args.source and set(args.source) - {m.SOURCE_ID for m in selected}:
        parser.error("Unknown source id")
    all_jobs: list[dict] = []
    successful_sources = 0
    report = []
    def collect(mod):
        started = monotonic()
        with _make_session() as session:
            jobs = mod.fetch(session)
        return jobs, round(monotonic() - started, 1)

    # Parallelize independent websites, never requests within one website.
    with ThreadPoolExecutor(max_workers=4) as pool:
      pending = {pool.submit(collect, mod): mod for mod in selected}
      for future in as_completed(pending):
        mod = pending[future]
        name = getattr(mod, "SOURCE_ID", mod.__name__)
        try:
            jobs, seconds = future.result()
        except Exception as e:
            print(f"[{name}] FAILED: {e}", file=sys.stderr)
            report.append({"source": name, "result": "failed", "error": str(e)[:300]})
            continue
        print(f"[{name}] {len(jobs)} jobs")
        report.append({"source": name, "result": "records_returned" if jobs else "empty_or_adapter_error", "raw_count": len(jobs), "seconds": seconds, "warnings": getattr(mod, "FETCH_WARNINGS", [])})
        successful_sources += 1
        for j in jobs:
            classify_job(j)
        all_jobs.extend(jobs)

    observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report_path = OUT.parent / "collection-report.json"
    if args.source and report_path.exists():
        report = [r for r in json.loads(report_path.read_text())["sources"] if r["source"] not in args.source] + report
    report_path.write_text(json.dumps({"attempted_at": observed_at, "sources": report}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not successful_sources or not all_jobs:
        print("No usable source records; keeping the previous snapshot.", file=sys.stderr)
        bundle()
        return 1
    for job in all_jobs:
        job["last_seen"] = observed_at
    if args.source and OUT.exists():
        previous = json.loads(OUT.read_text())["jobs"]
        all_jobs = [j for j in previous if j.get("source") not in args.source] + all_jobs
    all_jobs = list({j.get("source_url") or j.get("id"): j for j in all_jobs}.values())
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
    bundle()
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
