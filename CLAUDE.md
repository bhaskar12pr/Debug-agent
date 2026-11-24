# Debug-agent

AI debug agent for SoC verification engineers. Python toolkit (`debug_agent/`,
standard library only) + Claude Code subagent and skills (`.claude/`) +
verification collateral for the SOC_VERIF SoC (`dv/`).

## Layout
- `debug_agent/` - `logparse` (UVM, Verilator, Questa, VCS, Xcelium, [DBG]), `triage`, `vcd`, `rtl`, `evidence`, `cli`
  - optional backends, auto-detected: `rtl_slang` (pyslang) behind `rtl.load_rtl`, `wave_wellen` (pywellen) behind `vcd.open_waveform`.
    Without them the regex indexer and built-in VCD reader are used. Install: `pip install -e '.[fast]'`
- `dv/tb/tb_soc_top.sv` - directed SV testbench for `soc_top` (UVM message format, not UVM library)
- `dv/sva/` - bound checkers: `apb_protocol_checker`, `soc_decode_checker`, `soc_binds.sv`
- `dv/scripts/run_sim.sh`, `run_regression.sh` - Verilator build/run -> `runs/<test>_s<seed>/{sim.log,waves.vcd}`
- `examples/known_issues.md` - root-caused bugs; check new failures against it
- `.claude/agents/soc-debug.md` - the debug agent; skills in `.claude/skills/`

## Environment
- `SOC_VERIF` = path to the SOC_VERIF checkout (default `../SOC_VERIF` or `../soc_verif`)
- Simulator: Verilator 5.x (`--binary --timing --assert`). Commercial simulators: only the log parser and VCD reader are used; adapt `run_sim.sh`.
- `WAVES=fst dv/scripts/run_sim.sh ...` dumps `waves.fst` (about 20x smaller than VCD; reading it needs pywellen).
- Times in logs and VCD are ps (timescale 1ns/1ps).

## Commands
```
dv/scripts/run_regression.sh 10              # 3 directed tests + 10 random seeds
python3 -m debug_agent triage runs/
python3 -m debug_agent evidence runs/<run>
python3 -m debug_agent wave runs/<run>/waves.vcd --signals GLOB --from PS --to PS
python3 -m debug_agent drivers soc_top.u_apb_spi_master.PREADY
python3 -m debug_agent hier soc_top            # with pyslang: generate instances + resolved parameters
python3 -m debug_agent lint [--errors]         # pyslang compiler diagnostics on RTL + TB
python3 -m pytest -q
```

## Rules
- Never modify `SOC_VERIF/rtl/` (real, unmodified pulp-platform IP). Debug points go in `dv/sva/` via `bind`.
- Checker messages must use `[DBG][CATEGORY][instance] event key=value` and fire once per event.
- Every root-cause claim cites a log line, a signal value at a time, or an RTL file:line.
- After changing a parser, add a fixture under `tests/fixtures/` and a test.
- Keep the optional libraries optional: import them only inside `rtl_slang.py` / `wave_wellen.py`,
  and make sure `pytest` passes both with and without them (backend tests are parametrized/skipped).
