from pathlib import Path

from debug_agent.vcd import Vcd

VCD = Path(__file__).parent / "fixtures" / "tiny.vcd"


def test_header_and_find():
    v = Vcd(VCD)
    assert v.timescale_ps == 1000
    assert v.find("*valid") == ["top.u_sub.valid"]
    assert v.signals["top.data"].width == 8


def test_value_changes_and_x():
    v = Vcd(VCD)
    data, = v.load(["top.data"])
    assert data.value_at(9) == "00000000"
    assert data.value_at(10) == "10100101"
    assert data.value_at(25) == "xxxxxxxx"


def test_window_skips_clock_rows():
    v = Vcd(VCD)
    table = v.window(v.find("top.*"), 0, 20_000)
    lines = table.splitlines()
    assert lines[0].split("|")[0].strip() == "time(ps)"
    times = [l.split("|")[0].strip() for l in lines[1:] if "|" in l]
    assert times == ["0", "10000", "20000"]       # no rows for clk-only edges at 5/15 ns
    assert "0xa5" in table and "'bxxxxxxxx" in table
