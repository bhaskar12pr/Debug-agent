"""Regression triage: find failing runs and group them by first-failure signature."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .logparse import Event, first_failure, parse_log, signature

_PASS = re.compile(r"^TEST\s+\S+\s+SEED\s+\S+\s+PASSED|\bTEST PASSED\b|^\s*\*+\s*TEST PASSED", re.M)


@dataclass
class Run:
    name: str
    log: Path
    passed: bool
    first: Event | None
    n_failures: int


@dataclass
class Bucket:
    signature: str
    runs: list[Run] = field(default_factory=list)

    @property
    def example(self) -> Run:
        return self.runs[0]


def find_logs(paths: list[str | Path], log_name: str = "sim.log") -> list[Path]:
    logs: list[Path] = []
    for p in map(Path, paths):
        logs.extend([p] if p.is_file() else sorted(p.rglob(log_name)))
    return logs


def classify(log: Path) -> Run:
    events = parse_log(log)
    first = first_failure(events)
    text = log.read_text(errors="replace")
    passed = first is None and bool(_PASS.search(text))
    return Run(log.parent.name, log, passed, first, sum(e.is_failure for e in events))


def triage(paths: list[str | Path], log_name: str = "sim.log") -> tuple[list[Run], list[Bucket]]:
    runs = [classify(l) for l in find_logs(paths, log_name)]
    buckets: dict[str, Bucket] = {}
    for r in runs:
        if r.passed:
            continue
        sig = signature(r.first) if r.first else "NO_SUMMARY|crash, hang or killed before the end-of-test report"
        buckets.setdefault(sig, Bucket(sig)).runs.append(r)
    return runs, sorted(buckets.values(), key=lambda b: -len(b.runs))


def report(runs: list[Run], buckets: list[Bucket]) -> str:
    n_fail = sum(not r.passed for r in runs)
    out = [f"# Regression triage", "",
           f"{len(runs)} runs, {len(runs) - n_fail} passed, {n_fail} failed, "
           f"{len(buckets)} distinct first-failure signature(s)", ""]
    for i, b in enumerate(buckets, 1):
        ex = b.example
        out += [f"## Bucket {i}: {len(b.runs)} run(s)", "",
                f"- signature: `{b.signature}`",
                f"- runs: {', '.join(r.name for r in b.runs)}"]
        if ex.first:
            t = f" @ {ex.first.time:g}{ex.first.time_unit}" if ex.first.time is not None else ""
            out += [f"- first failure (example `{ex.name}`{t}): {ex.first.severity} "
                    f"[{ex.first.scope or ex.first.source}] {ex.first.message}",
                    f"- log: `{ex.log}:{ex.first.log_line}`"]
        out.append("")
    return "\n".join(out)
