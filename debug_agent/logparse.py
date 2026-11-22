"""Parse simulation logs into structured error events.

Understands the message formats of the common simulators so the agent never
has to read a raw multi-GB log:

* UVM report server   ``UVM_ERROR file(12) @ 100: reporter [ID] message``
* Verilator           ``[100] %Error: file.sv:12: Assertion failed in TOP.x.y: msg``
* Questa              ``** Error: msg`` (+ ``# Time: 100 ns  Scope: a.b File: f.sv Line: 12``)
* VCS                 ``"f.sv", 12: a.b.prop: started at 90ps failed at 100ps``
* Xcelium             ``xmsim: *E,ASRTST (f.sv,12): (time 100 NS) Assertion a.b.prop has failed``
* Debug points        ``[DBG][CATEGORY][instance] message`` (see dv/sva/), inside any of the above
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Iterator

SEVERITY_RANK = {"INFO": 0, "WARNING": 1, "ERROR": 2, "FATAL": 3}

_UVM = re.compile(
    r"^(?:#\s*)?UVM_(?P<sev>INFO|WARNING|ERROR|FATAL)\s+(?P<file>[^\s(]+)\((?P<line>\d+)\)\s+@\s+"
    r"(?P<time>[\d.]+)\s*(?P<unit>[a-z]*):\s+(?P<scope>\S+)\s+\[(?P<id>[^\]]+)\]\s+(?P<msg>.*)$")
_VERILATOR = re.compile(
    r"^(?:\[(?P<time>\d+)\]\s+)?%(?P<sev>Error|Warning|Fatal)(?:-\w+)?:\s+(?:(?P<file>[^\s:]+):(?P<line>\d+):\s+)?"
    r"(?:Assertion failed in (?P<scope>[^:\s]+):\s*)?(?P<msg>.*)$")
_QUESTA = re.compile(r"^#?\s*\*\*\s+(?P<sev>Error|Warning|Fatal|Failure)(?:\s*\([^)]*\))?:\s+(?P<msg>.*)$")
_QUESTA_LOC = re.compile(r"^#?\s*Time:\s+(?P<time>[\d.]+)\s*(?P<unit>[a-z]*)")
_QUESTA_KEY = {k: re.compile(rf"\b{k}:\s+(\S+)") for k in ("Scope", "File", "Line")}
_VCS = re.compile(
    r'^"(?P<file>[^"]+)",\s+(?P<line>\d+):\s+(?P<scope>\S+):\s+started at\s+(?P<start>[\d.]+)\s*(?P<unit>[a-z]+)\s+'
    r"failed at\s+(?P<time>[\d.]+)\s*[a-z]+")
_XCELIUM = re.compile(
    r"^\w+:\s+\*(?P<sev>[EWF]),(?P<id>\w+)\s+\((?P<file>[^,]+),(?P<line>\d+)\):\s+\(time\s+(?P<time>[\d.]+)\s+"
    r"(?P<unit>\w+)\)\s+(?P<msg>.*)$")
_DBG = re.compile(r"\[DBG\]\[(?P<cat>[^\]]+)\]\[(?P<inst>[^\]]+)\]\s*(?P<rest>.*)")

_UNIT_TO_PS = {"fs": 1e-3, "ps": 1.0, "ns": 1e3, "us": 1e6, "ms": 1e9, "s": 1e12}


@dataclass
class Event:
    severity: str                   # INFO | WARNING | ERROR | FATAL
    source: str                     # uvm | sva | sim
    message: str
    log_line: int                   # 1-based line in the log
    time: float | None = None       # in the log's own units
    time_unit: str = ""             # "" = simulator default (usually the timeprecision)
    scope: str = ""                 # reporter / assertion scope
    id: str = ""                    # UVM message id, assertion name or tool code
    file: str = ""
    line: int | None = None
    dbg_category: str = ""          # from [DBG][CAT][inst] debug points
    dbg_instance: str = ""
    raw: str = field(default="", repr=False)

    @property
    def is_failure(self) -> bool:
        return SEVERITY_RANK[self.severity] >= SEVERITY_RANK["ERROR"]

    def time_ps(self, default_unit: str = "ps") -> float | None:
        if self.time is None:
            return None
        return self.time * _UNIT_TO_PS.get((self.time_unit or default_unit).lower(), 1.0)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw")
        return d


def _sev(word: str) -> str:
    w = word.upper()
    return {"E": "ERROR", "W": "WARNING", "F": "FATAL", "FAILURE": "FATAL"}.get(w, w)


def _attach_dbg(ev: Event) -> Event:
    m = _DBG.search(ev.message)
    if m:
        ev.dbg_category, ev.dbg_instance = m["cat"], m["inst"]
        ev.source = "sva" if ev.source == "sim" else ev.source
    return ev


def parse_lines(lines: Iterable[str]) -> Iterator[Event]:
    pending_questa: Event | None = None
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")

        if pending_questa is not None:
            loc = _QUESTA_LOC.match(line)
            if loc:
                pending_questa.time = float(loc["time"])
                pending_questa.time_unit = loc["unit"] or ""
                kv = {k: (m[1] if (m := r.search(line)) else "") for k, r in _QUESTA_KEY.items()}
                pending_questa.scope, pending_questa.file = kv["Scope"], kv["File"]
                pending_questa.line = int(kv["Line"]) if kv["Line"].isdigit() else None
                pending_questa.id = pending_questa.scope.rsplit(".", 1)[-1]
            yield _attach_dbg(pending_questa)
            pending_questa = None
            if loc:
                continue

        if m := _UVM.match(line):
            yield _attach_dbg(Event(m["sev"], "uvm", m["msg"], n, float(m["time"]), m["unit"], m["scope"],
                                    m["id"], m["file"], int(m["line"]), raw=line))
        elif m := _VERILATOR.match(line):
            scope = m["scope"] or ""
            ev = Event(_sev(m["sev"]), "sva" if scope else "sim", m["msg"], n,
                       float(m["time"]) if m["time"] else None, "", scope,
                       scope.rsplit(".", 1)[-1] if scope else "", m["file"] or "",
                       int(m["line"]) if m["line"] else None, raw=line)
            yield _attach_dbg(ev)
        elif m := _QUESTA.match(line):
            pending_questa = Event(_sev(m["sev"]), "sim", m["msg"], n, raw=line)
        elif m := _VCS.match(line):
            yield Event("ERROR", "sva", f"assertion {m['scope']} failed (started at {m['start']}{m['unit']})", n,
                        float(m["time"]), m["unit"], m["scope"], m["scope"].rsplit(".", 1)[-1], m["file"],
                        int(m["line"]), raw=line)
        elif m := _XCELIUM.match(line):
            yield _attach_dbg(Event(_sev(m["sev"]), "sva" if "Assertion" in m["msg"] else "sim", m["msg"], n,
                                    float(m["time"]), m["unit"].lower(), "", m["id"], m["file"],
                                    int(m["line"]), raw=line))
    if pending_questa is not None:
        yield _attach_dbg(pending_questa)


def parse_log(path: str | Path) -> list[Event]:
    with open(path, errors="replace") as f:
        return list(parse_lines(f))


def failures(events: Iterable[Event]) -> list[Event]:
    return [e for e in events if e.is_failure]


def first_failure(events: Iterable[Event]) -> Event | None:
    """Earliest failure by simulation time (log order breaks ties / missing times).

    The first error is usually the cause; later ones (timeouts, scoreboard
    floods) are usually symptoms of it.
    """
    fails = failures(events)
    if not fails:
        return None
    return min(fails, key=lambda e: (e.time_ps() if e.time_ps() is not None else float("inf"), e.log_line))


_NORMALIZERS = [
    (re.compile(r"0x[0-9a-fA-F_]+"), "0x<HEX>"),
    (re.compile(r"'[bhdo][0-9a-fA-F_xXzZ]+"), "'<VAL>"),
    (re.compile(r"(?<![\w.])\d+(\.\d+)?\s*(fs|ps|ns|us|ms)\b"), "<TIME>"),
    (re.compile(r"\b\d+\b"), "<N>"),
    (re.compile(r"(/[^\s/:()]+)+/"), ""),           # strip directories from paths
]


def signature(ev: Event) -> str:
    """A seed/address/time-independent key used to group failures."""
    msg = ev.message
    for pat, rep in _NORMALIZERS:
        msg = pat.sub(rep, msg)
    head = ev.dbg_category and f"DBG:{ev.dbg_category}:{ev.dbg_instance}" or ev.id or ev.source
    return f"{ev.severity}|{head}|{msg.strip()}"


def context(path: str | Path, line_no: int, before: int = 20, after: int = 10) -> str:
    """Log lines around ``line_no`` (1-based), numbered, for the agent to read."""
    lines = Path(path).read_text(errors="replace").splitlines()
    lo, hi = max(0, line_no - 1 - before), min(len(lines), line_no + after)
    return "\n".join(f"{i + 1:6d}{'>' if i + 1 == line_no else ' '} {lines[i]}" for i in range(lo, hi))
