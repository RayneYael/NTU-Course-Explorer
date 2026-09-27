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


def term_order(sem_key: str) -> tuple[int, int]:
    """Chronological sort key: within an academic year Semester 1 < Semester 2 < Special Term."""
    year, sem = sem_key.replace("_", ";").split(";")
    return int(year), {"1": 1, "2": 2, "S": 3}.get(sem.upper(), 0)


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

    def _latest_semester_entries(self, complete_only: bool = False) -> dict[str, dict]:
        """sem_key -> manifest entry (with 'stored_in' and 'snapshot' resolved), newest first."""
        found: dict[str, dict] = {}
        for name in reversed(self.list()):
            m = self.manifest(name)
            for key, e in m["semesters"].items():
                if key in found or (complete_only and e["errors"]):
                    continue
                found[key] = {**e, "stored_in": e.get("stored_in", name), "snapshot": name}
        return found

    def available_semesters(self) -> list[dict]:
        """Every semester ever crawled successfully, newest term first.

        Each item: {"key": "2026;1", "label": "Acad Yr 2026 Semester 1", "fetched_at", "snapshot",
        "programmes", "courses"}. A semester stays available after later crawls skip it.
        """
        out = []
        for key, e in self._latest_semester_entries(complete_only=True).items():
            label = e.get("label") or self._load(e)["semester"].get("label", key)
            out.append({"key": key, "label": label, "fetched_at": e["fetched_at"],
                        "snapshot": e["snapshot"], "programmes": e["programmes"], "courses": e["courses"]})
        return sorted(out, key=lambda s: term_order(s["key"]), reverse=True)

    def load_current(self, sem_key: str) -> dict:
        """The newest successful crawl of one semester."""
        entry = self._latest_semester_entries(complete_only=True).get(sem_key)
        if entry is None:
            raise KeyError(f"semester {sem_key!r} has never been crawled successfully")
        return self._load(entry)

    def _load(self, entry: dict) -> dict:
        with gzip.open(self.snapshots / entry["stored_in"] / entry["file"], "rt", encoding="utf-8") as f:
            return normalize(json.load(f))

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
