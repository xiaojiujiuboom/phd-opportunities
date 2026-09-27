"""Generate a same-folder classic script so double-clicking index.html works."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def bundle():
    payload = {}
    for name in ("jobs", "rankings", "sources", "collection-report"):
        path = ROOT / "data" / (name + ".json")
        if path.exists():
            payload[name] = json.loads(path.read_text(encoding="utf-8"))
    (ROOT / "data" / "offline-data.js").write_text(
        "window.PHD_OFFLINE_DATA = " + json.dumps(payload, ensure_ascii=False)
        + ";\n", encoding="utf-8")


if __name__ == "__main__":
    bundle()
