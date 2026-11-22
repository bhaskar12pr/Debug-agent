import shutil
from pathlib import Path

from debug_agent.triage import triage

FX = Path(__file__).parent / "fixtures"


def test_groups_failures_by_signature(tmp_path):
    for name, src in [("a_s1", "verilator_bus_hang.log"), ("a_s2", "verilator_bus_hang.log"),
                      ("b_s1", "verilator_scb_mismatch.log"), ("c_s1", "verilator_pass.log")]:
        (tmp_path / name).mkdir()
        shutil.copy(FX / src, tmp_path / name / "sim.log")
    (tmp_path / "d_s1").mkdir()
    (tmp_path / "d_s1" / "sim.log").write_text("UVM_INFO t.sv(1) @ 0: x [T] started\n")   # died silently

    runs, buckets = triage([tmp_path])
    assert sum(r.passed for r in runs) == 1
    assert [len(b.runs) for b in buckets] == [2, 1, 1]
    assert buckets[0].signature.startswith("ERROR|DBG:DECODE:soc_top.u_apb_node|")
    assert any(b.signature.startswith("NO_SUMMARY") for b in buckets)
