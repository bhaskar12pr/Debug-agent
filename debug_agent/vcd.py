"""Minimal streaming VCD reader: list signals and query values in a time window.

Only the signals asked for are kept in memory, so it works on large dumps.
FSDB is not readable without vendor libraries; convert with ``fsdb2vcd``
(Synopsys Verdi) for just the scopes and time window you need.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path

_UNIT_TO_PS = {"fs": 1e-3, "ps": 1.0, "ns": 1e3, "us": 1e6, "ms": 1e9, "s": 1e12}


@dataclass
class Signal:
    path: str           # dotted hierarchical path, e.g. TOP.tb.dut.paddr
    code: str
    width: int
    changes: list[tuple[int, str]] = field(default_factory=list)   # (time, binary string)

    def value_at(self, t: int) -> str | None:
        val = None
        for ct, v in self.changes:
            if ct > t:
                break
            val = v
        return val


def fmt_value(v: str | None, width: int) -> str:
    if v is None:
        return "?"
    if width == 1:
        return v
    if set(v) <= {"0", "1"}:
        return f"0x{int(v, 2):0{(width + 3) // 4}x}"
    return f"'b{v}"   # contains x/z


def _short_names(paths: list[str]) -> list[str]:
    """Shortest dotted suffix that is unique among ``paths``."""
    names = []
    for p in paths:
        parts = p.split(".")
        for k in range(1, len(parts) + 1):
            cand = ".".join(parts[-k:])
            if sum(q == cand or q.endswith("." + cand) for q in paths) == 1:
                break
        names.append(cand)
    return names


class Vcd:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.timescale_ps = 1.0
        self.signals: dict[str, Signal] = {}       # path -> Signal
        self._by_code: dict[str, list[Signal]] = {}
        self._header_end = 0
        self._read_header()

    def _read_header(self) -> None:
        scope: list[str] = []
        text_ts = ""
        with open(self.path, errors="replace") as f:
            in_ts = False
            while line := f.readline():
                tok = line.split()
                if not tok:
                    continue
                if in_ts:
                    text_ts += " " + " ".join(t for t in tok if t != "$end")
                    in_ts = "$end" not in tok
                    continue
                if tok[0] == "$timescale":
                    text_ts = " ".join(t for t in tok[1:] if t != "$end")
                    in_ts = "$end" not in tok
                elif tok[0] == "$scope":
                    scope.append(tok[2])
                elif tok[0] == "$upscope":
                    scope.pop()
                elif tok[0] == "$var":
                    width, code, name = int(tok[2]), tok[3], tok[4]
                    sig = Signal(".".join(scope + [name]), code, width)
                    self.signals[sig.path] = sig
                    self._by_code.setdefault(code, []).append(sig)
                elif tok[0] == "$enddefinitions":
                    self._header_end = f.tell()
                    break
        m = re.match(r"\s*(\d+)\s*([a-z]+)", text_ts)
        if m:
            self.timescale_ps = int(m[1]) * _UNIT_TO_PS[m[2]]

    def find(self, pattern: str) -> list[str]:
        """Signal paths matching a glob (``*paddr*``) or a plain substring."""
        if any(c in pattern for c in "*?["):
            return [p for p in self.signals if fnmatch.fnmatchcase(p, pattern)]
        return [p for p in self.signals if pattern in p]

    def load(self, paths: list[str]) -> list[Signal]:
        """Read value changes for the given signal paths only."""
        wanted = {self.signals[p].code for p in paths}
        for p in paths:
            self.signals[p].changes.clear()
        t = 0
        with open(self.path, errors="replace") as f:
            f.seek(self._header_end)
            for line in f:
                line = line.strip()
                if not line or line[0] == "$":
                    continue
                c = line[0]
                if c == "#":
                    t = int(line[1:])
                elif c in "01xzXZ":
                    code = line[1:]
                    if code in wanted:
                        for s in self._by_code[code]:
                            s.changes.append((t, c.lower()))
                elif c in "bB":
                    val, code = line[1:].split()
                    if code in wanted:
                        for s in self._by_code[code]:
                            s.changes.append((t, val.lower().zfill(s.width)))
        return [self.signals[p] for p in paths]

    def window(self, paths: list[str], t0_ps: float, t1_ps: float, max_rows: int = 200,
               clock_pattern: str = r"(clk|clock|hclk)(_i)?$") -> str:
        """Text table: values at t0, then one row per time a non-clock signal changes.

        Clock edges alone do not create rows, and signals that never change in
        the window (parameters, tied inputs) are listed once below the table.
        """
        sigs = self.load(paths)
        t0, t1 = int(t0_ps / self.timescale_ps), int(t1_ps / self.timescale_ps)
        is_clk = [bool(re.search(clock_pattern, s.path.split(".")[-1], re.I)) for s in sigs]
        moving = [s for s, c in zip(sigs, is_clk)
                  if not c and any(t0 < t <= t1 for t, _ in s.changes)]
        static = [s for s, c in zip(sigs, is_clk) if not c and s not in moving]
        times = sorted({t for s in moving for t, _ in s.changes if t0 < t <= t1})
        names = _short_names([s.path for s in moving])
        rows = [["time(ps)"] + names]
        rows.append([f"{t0 * self.timescale_ps:g}"] + [fmt_value(s.value_at(t0), s.width) for s in moving])
        for t in times[:max_rows]:
            rows.append([f"{t * self.timescale_ps:g}"] + [fmt_value(s.value_at(t), s.width) for s in moving])
        widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
        out = [" | ".join(c.rjust(w) for c, w in zip(r, widths)) for r in rows]
        if len(times) > max_rows:
            out.append(f"... {len(times) - max_rows} more change times")
        out.append("signals:")
        out += [f"  {n} = {s.path}" for n, s in zip(names, moving)]
        if static:
            out.append("unchanged in window:")
            out += [f"  {s.path} = {fmt_value(s.value_at(t0), s.width)}" for s in static]
        return "\n".join(out)
