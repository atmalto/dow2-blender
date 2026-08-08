"""Result collection and per-category log file output."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Status = Literal["passed", "failed", "skipped"]


@dataclass
class TestRecord:
    name: str
    category: str
    status: Status
    detail: str = ""


@dataclass
class ResultLog:
    """Collects test outcomes and writes them into per-purpose log files.

    Buckets written on ``flush()``:
      - unchecked.log        : skipped tests (missing data / assets)
      - failures.log         : every failure with detail
      - by_category/<cat>.log: failures grouped by feature category
    """

    log_dir: Path
    records: list[TestRecord] = field(default_factory=list)

    def add(self, name: str, category: str, status: Status, detail: str = "") -> None:
        self.records.append(TestRecord(name, category, status, detail))

    # -- queries ----------------------------------------------------------
    def counts(self) -> dict[str, int]:
        out = {"passed": 0, "failed": 0, "skipped": 0}
        for r in self.records:
            out[r.status] += 1
        return out

    @property
    def failed(self) -> list[TestRecord]:
        return [r for r in self.records if r.status == "failed"]

    @property
    def skipped(self) -> list[TestRecord]:
        return [r for r in self.records if r.status == "skipped"]

    # -- output -----------------------------------------------------------
    def flush(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        by_cat = self.log_dir / "by_category"
        by_cat.mkdir(exist_ok=True)
        stamp = _dt.datetime.now().isoformat(timespec="seconds")

        header = f"# DoW2 Tools test run ; {stamp}\n"

        (self.log_dir / "unchecked.log").write_text(
            header + "".join(f"[SKIP] {r.category}/{r.name}: {r.detail}\n" for r in self.skipped),
            encoding="utf-8",
        )
        (self.log_dir / "failures.log").write_text(
            header + "".join(f"[FAIL] {r.category}/{r.name}: {r.detail}\n" for r in self.failed),
            encoding="utf-8",
        )

        cats: dict[str, list[TestRecord]] = {}
        for r in self.failed:
            cats.setdefault(r.category, []).append(r)
        for cat, recs in cats.items():
            safe = cat.replace("/", "_")
            (by_cat / f"{safe}.log").write_text(
                header + "".join(f"[FAIL] {r.name}: {r.detail}\n" for r in recs),
                encoding="utf-8",
            )

    def summary_line(self) -> str:
        c = self.counts()
        return f"passed={c['passed']} failed={c['failed']} skipped={c['skipped']}"
