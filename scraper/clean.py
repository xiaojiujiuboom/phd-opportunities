"""Remove expired, unconfirmed and stale PhD records without claiming a refresh."""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from eligibility import filter_phds


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    target = root / "data" / "jobs.json"
    data = json.loads(target.read_text(encoding="utf-8"))
    original = len(data["jobs"])
    kept, counts = filter_phds(data["jobs"], today=args.as_of, observed_at=data.get("updated_at"))
    data.update(total=len(kept), jobs=kept)
    data["cleanup"] = {"as_of": args.as_of.isoformat(), "original_total": original,
                       "retained_total": len(kept), "removed_by_reason": counts}
    data["cleaned_at"] = datetime.now(timezone.utc).isoformat()
    # updated_at remains the original successful collection timestamp.
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data["cleanup"], ensure_ascii=False))


if __name__ == "__main__":
    main()
