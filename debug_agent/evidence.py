"""Build a compact "evidence pack" for one failing run.

The pack is what the LLM agent reads instead of the raw log and waveform:
first failure, the distinct failures that followed it, log context, a
waveform window around the first failure, and the RTL behind the reporting
instance. A few KB instead of MB/GB.
"""
from __future__ import annotations

import re
from pathlib import Path

from .logparse import Event, context, failures, first_failure, parse_log, signature
from .rtl import load_rtl
from .vcd import Vcd
from .vcd import open_waveform


def _failure_timeline(events: list[Event]) -> list[str]:
    seen: dict[str, list[Event]] = {}
    for e in failures(events):
        seen.setdefault(signature(e), []).append(e)
    rows = []
    for evs in sorted(seen.values(), key=lambda v: (v[0].time_ps() or float("inf"), v[0].log_line)):
        e = evs[0]
        t = f"{e.time:g}{e.time_unit}" if e.time is not None else "?"
        rows.append(f"| {t} | {e.severity} | {e.source} | `{e.scope or '-'}` | {e.message[:160]} | {len(evs)} |")
    return ["| first at | severity | source | scope | message | count |", "|---|---|---|---|---|---|"] + rows


def _wave_signals(vcd: Vcd, ev: Event, extra: list[str]) -> list[str]:
    picked: list[str] = []
    for pat in extra:
        picked += vcd.find(pat)
    if ev.scope:
        # A bound checker's own ports are exactly the signals its assertion looked at.
        scope = ev.scope.rsplit(".", 1)[0] if ev.scope.rsplit(".", 1)[-1].startswith(("a_", "assert")) else ev.scope
        picked += [p for p in vcd.signals if p.rsplit(".", 1)[0] == scope]
    seen, out = set(), []
    for p in picked:
        if p not in seen and vcd.signals[p].width <= 256:
            seen.add(p)
            out.append(p)
    return out[:24]


def _rtl_section(idx, ev: Event) -> list[str]:
    out: list[str] = []
    inst = ev.dbg_instance or ""
    if not inst:
        return out
    try:
        mod, rest = idx.resolve(inst)
    except KeyError:
        return [f"- instance `{inst}` not found in the indexed RTL"]
    out.append(f"- `{inst}` is module `{mod.name}` in `{mod.file}:{mod.line}`")
    # Signals named in the message (e.g. pready_o), traced to their drivers.
    for name in sorted(set(re.findall(r"\b([A-Za-z_]\w*)\b", ev.message))):
        if name in mod.ports:
            for d in idx.drivers(f"{inst}.{name}"):
                out.append(f"  - `{d.path}` driven at `{d.file}:{d.line}` ({d.kind}): `{d.text}`")
    return out


def build(run_dir: str | Path, rtl_roots: list[str | Path] | None = None, signals: list[str] | None = None,
          before_ps: float = 200_000, after_ps: float = 50_000, rtl_backend: str = "auto",
          wave_backend: str = "auto") -> str:
    run_dir = Path(run_dir)
    log = run_dir / "sim.log" if run_dir.is_dir() else run_dir
    run_dir = log.parent
    events = parse_log(log)
    first = first_failure(events)
    out = [f"# Evidence pack: `{run_dir.name}`", "", f"- log: `{log}`"]
    if first is None:
        out += ["- no failures found in the log (check for a missing end-of-test summary: crash or hang)"]
        return "\n".join(out)

    t = f"{first.time:g}{first.time_unit}" if first.time is not None else "unknown time"
    out += [f"- failures: {len(failures(events))} total, {len({signature(e) for e in failures(events)})} distinct",
            "", "## First failure (most likely the cause; later ones are often symptoms)", "",
            f"- time: {t}", f"- severity/source: {first.severity} / {first.source}",
            f"- scope: `{first.scope or '-'}`  id: `{first.id or '-'}`",
            f"- message: {first.message}",
            f"- reported at: `{first.file}:{first.line}`" if first.file else "- reported at: -",
            "", "## Failure timeline (deduplicated)", "", *_failure_timeline(events),
            "", "## Log context", "", "```", context(log, first.log_line), "```"]

    vcd_path = next((run_dir / n for n in ("waves.fst", "waves.vcd") if (run_dir / n).exists()), None)
    if vcd_path is not None and first.time_ps() is not None:
        vcd = open_waveform(vcd_path, wave_backend)
        sigs = _wave_signals(vcd, first, signals or [])
        if sigs:
            t0 = max(0.0, first.time_ps() - before_ps)
            out += ["", f"## Waveform window {t0:g}..{first.time_ps() + after_ps:g} ps "
                    f"(`{vcd_path.name}`, {getattr(vcd, 'backend', 'vcd')})", "", "```",
                    vcd.window(sigs, t0, first.time_ps() + after_ps), "```"]
        else:
            out += ["", "## Waveform", "", f"- `{vcd_path}` exists; pass --signals to pick signals"]

    if rtl_roots:
        idx = load_rtl(rtl_roots, rtl_backend)
        sec = _rtl_section(idx, first)
        if sec:
            out += ["", f"## RTL ({idx.backend})", "", *sec]
    return "\n".join(out)
