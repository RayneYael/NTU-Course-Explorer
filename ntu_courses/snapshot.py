"""Append-only snapshot archive.

data/snapshots/<YYYY-MM-DDTHHMMSSZ>/
    manifest.json        crawl time, per-semester hash / counts / errors, and for
                         unchanged semesters a pointer to the snapshot holding the data
    <year>_<sem>.json.gz one file per semester that changed since the previous snapshot
data/LATEST             name of the newest complete snapshot

Snapshots are written to a '.tmp' directory and renamed only when finished, so a
crashed crawl never leaves a half-written snapshot. Existing snapshots are never modified.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .crawler import normalize

FORMAT_VERSION = 1


def _hash(data: dict) -> str:
    """Content hash, ignoring the crawl timestamp."""
    body = {k: v for k, v in data.items() if k != "fetched_at"}
    raw = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class Archive:
    def __init__(self, root: str | Path = "data"):
        self.root = Path(root)
        self.snapshots = self.root / "snapshots"

    # ------------------------------------------------------------------ read
    def latest(self) -> str | None:
        f = self.root / "LATEST"
        return f.read_text().strip() if f.exists() else None

    def list(self) -> list[str]:
        if not self.snapshots.exists():
            return []
        return sorted(p.name for p in self.snapshots.iterdir()
                      if p.is_dir() and not p.name.endswith(".tmp"))

    def manifest(self, name: str) -> dict:
        return json.loads((self.snapshots / name / "manifest.json").read_text())

    def load_semester(self, name: str, sem_key: str) -> dict:
        """Load a semester from a snapshot, following 'unchanged' pointers."""
        entry = self.manifest(name)["semesters"][sem_key]
        path = self.snapshots / entry.get("stored_in", name) / entry["file"]
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return normalize(json.load(f))

    def _latest_semester_entries(self) -> dict[str, dict]:
        """sem_key -> manifest entry (with 'stored_in' resolved) from the newest snapshots."""
        found: dict[str, dict] = {}
        for name in reversed(self.list()):
            for key, e in self.manifest(name)["semesters"].items():
                if key not in found:
                    found[key] = {**e, "stored_in": e.get("stored_in", name)}
        return found

    # ------------------------------------------------------------------ write
    def write(self, semesters: list[dict], tool_version: str = "", note: str = "") -> str:
        """Write a new snapshot for the given crawled semesters; returns its name.

        LATEST is only moved when every semester crawled without errors.
        """
        now = datetime.now(timezone.utc)
        name = now.strftime("%Y-%m-%dT%H%M%SZ")
        final = self.snapshots / name
        if final.exists():
            raise FileExistsError(final)
        tmp = self.snapshots / (name + ".tmp")
        tmp.mkdir(parents=True)

        previous = self._latest_semester_entries()
        manifest = {"format_version": FORMAT_VERSION, "created_at": now.isoformat(timespec="seconds"),
                    "tool_version": tool_version, "semesters": {}}
        if note:
            manifest["note"] = note
        complete = True
        for data in semesters:
            key = data["semester"]["key"]
            fname = key.replace(";", "_") + ".json.gz"
            digest = _hash(data)
            entry = {
                "label": data["semester"].get("label", ""), "file": fname, "sha256": digest, "fetched_at": data["fetched_at"],
                "programmes": len(data["programmes"]), "courses": len(data["courses"]),
                "indexes": sum(len(c["indexes"]) for c in data["courses"].values()),
                "errors": data["errors"],
            }
            prev = previous.get(key)
            if prev and prev["sha256"] == digest:
                entry["stored_in"] = prev["stored_in"]  # unchanged: point at existing file
            else:
                with gzip.open(tmp / fname, "wt", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
                if prev:
                    entry["previous"] = prev["stored_in"]
            manifest["semesters"][key] = entry
            complete &= not data["errors"]

        manifest["complete"] = complete
        (tmp / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        os.rename(tmp, final)
        if complete:
            (self.root / "LATEST.tmp").write_text(name + "\n")
            os.replace(self.root / "LATEST.tmp", self.root / "LATEST")
        return name
