from importlib.util import find_spec
from pathlib import Path

import pytest

from debug_agent.vcd import Vcd

FX = Path(__file__).parent / "fixtures"
needs_wellen = pytest.mark.skipif(find_spec("pywellen") is None, reason="pywellen not installed")


@needs_wellen
def test_wellen_matches_builtin_reader_on_vcd():
    from debug_agent.wave_wellen import WellenWave
    a, b = Vcd(FX / "tiny.vcd"), WellenWave(FX / "tiny.vcd")
    assert set(a.signals) == set(b.signals)
    assert a.timescale_ps == b.timescale_ps == 1000
    paths = a.find("top.*")
    assert a.window(paths, 0, 20_000) == b.window(paths, 0, 20_000)


@needs_wellen
def test_fst_from_verilator_run():
    from debug_agent.vcd import open_waveform
    w = open_waveform(FX / "timer_count.fst")
    assert w.backend == "pywellen"
    regs, = w.load(w.find("*TIMER_GEN[0].timer_i.regs_q"))      # brackets match literally
    # TIMER (top 32 bits of regs_q) counts up every cycle once enabled: KI-002
    timer = [int(v, 2) >> 64 for t, v in regs.changes if 115_000 <= t <= 135_000]
    assert timer == [0x100, 0x101, 0x102]


def test_brackets_in_patterns_are_literal():
    v = Vcd(FX / "tiny.vcd")
    v.signals["top.bus[0]"] = v.signals["top.data"]
    assert v.find("*bus[0]") == ["top.bus[0]"]
