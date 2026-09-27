"""Export the snapshot archive as static JSON for the web UI (web/public/data by default).

out/
  semesters.json   [{key, label, fetched_at, programmes, courses, file}], newest term first
  2026_1.json      one minified semester (format 2 layout, see crawler.py)
"""
from __future__ import annotations

import json
from pathlib import Path

from .snapshot import Archive


def export_web(archive: Archive, out: str | Path) -> list[dict]:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for sem in archive.available_semesters():
        key = sem["key"].replace(";", "_")
        data = archive.load_current(sem["key"])
        data["semester"]["key"] = key
        for p in data["programmes"]:
            p.pop("content_value", None)  # internal to the scraper
        fname = f"{key}.json"
        _write(out / fname, data)
        index.append({"key": key, "label": sem["label"], "fetched_at": sem["fetched_at"],
                      "programmes": sem["programmes"], "courses": sem["courses"], "file": fname})
    keep = {"semesters.json", *(s["file"] for s in index)}
    for stale in out.glob("*.json"):
        if stale.name not in keep:
            stale.unlink()
    _write(out / "semesters.json", index)
    return index


def _write(path: Path, obj) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)
