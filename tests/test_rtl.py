from pathlib import Path

from debug_agent.rtl import RtlIndex

RTL = Path(__file__).parent / "fixtures" / "rtl"


def test_resolve_instances():
    idx = RtlIndex([RTL])
    mod, rest = idx.resolve("TOP.top.u_mid.u_leaf.rdy_o")
    assert mod.name == "leaf" and rest == ["rdy_o"]


def test_drivers_trace_through_two_levels_of_ports():
    ds = RtlIndex([RTL]).drivers("top.ready")
    kinds = [(d.path, d.kind) for d in ds]
    assert ("top.u_mid.u_leaf.rdy_o", "tie-off") in kinds
    tie = next(d for d in ds if d.kind == "tie-off")
    assert tie.line == 17 and "assign rdy_o = 1'b1" in tie.text


def test_procedural_driver_line():
    ds = RtlIndex([RTL]).drivers("top.busy")
    assert [(d.kind, d.line) for d in ds] == [("procedural", 5)]


def test_hierarchy():
    h = RtlIndex([RTL]).hierarchy("top")
    assert any(l.startswith("top.u_mid.u_leaf  [leaf]") for l in h)
