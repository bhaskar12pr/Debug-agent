"""pywellen backend for waveforms: fast compiled reader for VCD, FST and GHW.

Same interface as :class:`debug_agent.vcd.Vcd` (``signals``, ``find``,
``load``, ``window``). FST dumps are 10-100x smaller than VCD; Verilator
writes them with ``--trace-fst`` (``WAVES=fst dv/scripts/run_sim.sh``).

Optional dependency: ``pip install pywellen``.
"""
from __future__ import annotations

import re
from pathlib import Path

import pywellen

from .vcd import Signal, Vcd

_UNIT_PS = {"fs": 1e-3, "ps": 1.0, "ns": 1e3, "us": 1e6, "ms": 1e9, "s": 1e12}


def _to_bin(val, width: int) -> str:
    if isinstance(val, int):
        return format(val, "b").zfill(width)
    return str(val).lower().zfill(width)


class WellenWave(Vcd):
    backend = "pywellen"

    def __init__(self, path: str | Path):          # noqa: super().__init__ reads VCD text; not wanted here
        self.path = Path(path)
        self.wave = pywellen.Waveform(str(self.path))
        ts = self.wave.timescale
        unit = re.search(r"(fs|ps|ns|us|ms|s)\b", str(ts).lower())
        self.timescale_ps = (ts.factor if ts else 1) * _UNIT_PS[unit[1] if unit else "ps"]
        self.signals: dict[str, Signal] = {}
        self._vars = {}
        for v in self.wave.all_vars():
            p = v.full_name
            self.signals[p] = Signal(p, str(v.signal_ref), v.bitwidth or 1)
            self._vars[p] = v

    def load(self, paths: list[str]) -> list[Signal]:
        by_id: dict[str, list[Signal]] = {}
        for p in paths:
            s = self.signals[p]
            s.changes.clear()
            by_id.setdefault(s.code, []).append(s)
        uniq = {self.signals[p].code: self._vars[p] for p in paths}

        def cb(t, sid, val):
            for s in by_id.get(str(sid), ()):
                b = _to_bin(val, s.width)
                if not s.changes or s.changes[-1][1] != b:
                    s.changes.append((int(t), b))

        self.wave.stream_changes(cb, list(uniq.values()))
        return [self.signals[p] for p in paths]

