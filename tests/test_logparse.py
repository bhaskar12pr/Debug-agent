from pathlib import Path

from debug_agent.logparse import first_failure, parse_log, signature

FX = Path(__file__).parent / "fixtures"


def test_verilator_first_failure_is_the_cause_not_the_timeout():
    ev = first_failure(parse_log(FX / "verilator_bus_hang.log"))
    assert ev.source == "sva"
    assert ev.time == 195000
    assert ev.id == "a_addr_mapped"
    assert ev.dbg_category == "DECODE" and ev.dbg_instance == "soc_top.u_apb_node"


def test_verilator_all_failures_parsed():
    evs = [e for e in parse_log(FX / "verilator_bus_hang.log") if e.is_failure]
    assert [e.severity for e in evs] == ["ERROR", "ERROR", "FATAL"]
    assert evs[2].source == "uvm" and evs[2].id == "APB_TIMEOUT"


def test_uvm_summary_lines_are_not_errors():
    assert first_failure(parse_log(FX / "verilator_pass.log")) is None


def test_uvm_scoreboard_mismatch():
    ev = first_failure(parse_log(FX / "verilator_scb_mismatch.log"))
    assert (ev.severity, ev.id, ev.time) == ("ERROR", "SCB_MISMATCH", 145000)


def test_questa_error_picks_up_time_and_scope():
    ev = first_failure(parse_log(FX / "questa_assert.log"))
    assert ev.time_ps() == 1_250_000
    assert ev.scope == "tb.dut.u_chk_uart.a_stall"
    assert ev.file == "apb_protocol_checker.sv" and ev.line == 51
    assert ev.dbg_instance == "soc_top.u_apb_uart"


def test_vcs_assertion():
    ev = first_failure(parse_log(FX / "vcs_assert.log"))
    assert ev.source == "sva" and ev.id == "a_access_follows_setup" and ev.time_ps() == 105000


def test_xcelium_assertion_before_fatal():
    ev = first_failure(parse_log(FX / "xcelium_assert.log"))
    assert ev.source == "sva" and ev.time_ps() == 205_000 and ev.id == "ASRTST"


def test_signature_ignores_addresses_and_numbers():
    a = first_failure(parse_log(FX / "verilator_bus_hang.log"))
    b = first_failure(parse_log(FX / "verilator_bus_hang.log"))
    b.message = b.message.replace("0x10004024", "0x1000403c")
    assert signature(a) == signature(b)
    assert "0x<HEX>" in signature(a)
