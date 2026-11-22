"""Command line: python -m debug_agent <command> ...

  triage    <runs_dir|log>...                 group failing runs by first-failure signature
  first     <log>                             first failure + log context
  evidence  <run_dir> [--rtl DIR]... [--signals GLOB]...   evidence pack for one failing run
  wave      <vcd> --signals GLOB... --from PS --to PS      value table for a time window
  signals   <vcd> PATTERN                     list signal paths matching a glob/substring
  drivers   HIER.PATH --rtl DIR...            what drives a signal (traces into sub-modules)
  hier      TOP --rtl DIR...                  instance hierarchy with source files
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import evidence, logparse, triage
from .rtl import RtlIndex
from .vcd import Vcd


def _default_rtl() -> list[str]:
    roots = []
    soc = os.environ.get("SOC_VERIF")
    here = Path(__file__).resolve().parent.parent
    for c in ([soc] if soc else []) + [str(here.parent / "SOC_VERIF"), str(here.parent / "soc_verif")]:
        if c and (Path(c) / "rtl").is_dir():
            roots.append(str(Path(c) / "rtl"))
            break
    if (here / "dv").is_dir():
        roots.append(str(here / "dv"))
    return roots


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="debug_agent", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("triage"); p.add_argument("paths", nargs="+"); p.add_argument("--json", action="store_true")
    p.add_argument("--log-name", default="sim.log")
    p = sub.add_parser("first"); p.add_argument("log"); p.add_argument("--before", type=int, default=20)
    p.add_argument("--after", type=int, default=10); p.add_argument("--json", action="store_true")
    p = sub.add_parser("evidence"); p.add_argument("run"); p.add_argument("--rtl", action="append")
    p.add_argument("--signals", action="append", default=[])
    p.add_argument("--before-ps", type=float, default=200_000); p.add_argument("--after-ps", type=float, default=50_000)
    p = sub.add_parser("wave"); p.add_argument("vcd"); p.add_argument("--signals", action="append", required=True)
    p.add_argument("--from", dest="t0", type=float, required=True); p.add_argument("--to", dest="t1", type=float, required=True)
    p = sub.add_parser("signals"); p.add_argument("vcd"); p.add_argument("pattern")
    p = sub.add_parser("drivers"); p.add_argument("path"); p.add_argument("--rtl", action="append")
    p.add_argument("--depth", type=int, default=4)
    p = sub.add_parser("hier"); p.add_argument("top"); p.add_argument("--rtl", action="append")

    a = ap.parse_args(argv)

    if a.cmd == "triage":
        runs, buckets = triage.triage(a.paths, a.log_name)
        if a.json:
            print(json.dumps([{"signature": b.signature, "runs": [str(r.log) for r in b.runs],
                               "first": b.example.first.to_dict() if b.example.first else None}
                              for b in buckets], indent=2))
        else:
            print(triage.report(runs, buckets))
        return 0
    if a.cmd == "first":
        ev = logparse.first_failure(logparse.parse_log(a.log))
        if ev is None:
            print("no failures found"); return 1
        if a.json:
            print(json.dumps(ev.to_dict(), indent=2)); return 0
        print(f"{ev.severity} [{ev.source}] t={ev.time} scope={ev.scope or '-'} id={ev.id or '-'}\n{ev.message}\n")
        print(logparse.context(a.log, ev.log_line, a.before, a.after)); return 0
    if a.cmd == "evidence":
        print(evidence.build(a.run, a.rtl or _default_rtl(), a.signals, a.before_ps, a.after_ps)); return 0
    if a.cmd == "wave":
        v = Vcd(a.vcd)
        paths = [p for g in a.signals for p in v.find(g)]
        if not paths:
            print("no signals matched", file=sys.stderr); return 1
        print(v.window(paths, a.t0, a.t1)); return 0
    if a.cmd == "signals":
        print("\n".join(Vcd(a.vcd).find(a.pattern))); return 0
    if a.cmd == "drivers":
        idx = RtlIndex(a.rtl or _default_rtl())
        ds = idx.drivers(a.path, a.depth)
        if not ds:
            print(f"no drivers found for {a.path}"); return 1
        for d in ds:
            print(f"{d.path}\n    {d.kind:10s} {d.file}:{d.line}: {d.text}")
        return 0
    if a.cmd == "hier":
        print("\n".join(RtlIndex(a.rtl or _default_rtl()).hierarchy(a.top))); return 0
    return 2
