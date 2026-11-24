from pathlib import Path

import pytest

from debug_agent.rtl import RtlIndex, load_rtl

RTL = Path(__file__).parent / "fixtures" / "rtl"
BACKENDS = ["regex", pytest.param("slang", marks=pytest.mark.skipif(
    __import__("importlib").util.find_spec("pyslang") is None, reason="pyslang not installed"))]


@pytest.fixture(params=BACKENDS)
def idx(request):
    return load_rtl([RTL], request.param)


def test_backend_selected(idx):
    assert idx.backend in ("regex", "pyslang")


def test_resolve_instances(idx):
    mod, rest = idx.resolve("TOP.top.u_mid.u_leaf.rdy_o")
    assert mod.name == "leaf" and rest == ["rdy_o"]


def test_drivers_trace_through_two_levels_of_ports(idx):
    ds = idx.drivers("top.ready")
    assert ("top.u_mid.u_leaf.rdy_o", "tie-off") in [(d.path, d.kind) for d in ds]
    tie = next(d for d in ds if d.kind == "tie-off")
    assert tie.line == 17 and "assign rdy_o = 1'b1" in tie.text


def test_procedural_driver_line(idx):
    assert [(d.kind, d.line) for d in idx.drivers("top.busy")] == [("procedural", 5)]


def test_hierarchy(idx):
    h = idx.hierarchy("top")
    assert any(l.startswith("top.u_mid.u_leaf  [leaf]") for l in h)


# ---- things only the pyslang backend gets right --------------------------------


@pytest.mark.skipif(__import__("importlib").util.find_spec("pyslang") is None, reason="pyslang not installed")
def test_slang_sees_generate_instances_and_parameters():
    s = load_rtl([RTL], "slang")
    h = s.hierarchy("gen_top")
    assert any(l.startswith("gen_top.GEN[0].u_cell  [ok_cell]") for l in h)
    assert any(l.startswith("gen_top.GEN[1].u_cell  [ok_cell]") for l in h)
    ds = s.drivers("gen_top.GEN[1].u_cell.ok_o")
    assert [(d.kind, d.line) for d in ds] == [("tie-off", 11)]       # through the `ONE macro
    assert not s.errors


def test_regex_misses_generate_instances():
    h = RtlIndex([RTL]).hierarchy("gen_top")
    assert not any("GEN[0]" in l for l in h)        # documents the regex limitation
