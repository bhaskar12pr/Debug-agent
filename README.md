# Debug-agent

An AI debug agent for SoC verification engineers. It triages a regression,
root-causes each distinct failure from **log + waveform + RTL** evidence, and
reports cause, classification and fix: the same steps a verification engineer
follows, done by Claude using small tools that turn huge logs and dumps into a
few KB of evidence.

Built and tested against [SOC_VERIF](https://github.com/bhaskar12pr/SOC_VERIF)
(4 real pulp-platform APB peripherals: GPIO, UART, timer, SPI, on `apb_node`),
the sibling of [coverage_agent](https://github.com/bhaskar12pr/coverage_agent).

## Pieces

| Part | What it does |
|---|---|
| `.claude/agents/soc-debug.md` | The agent: workflow, evidence rules, report format |
| `.claude/skills/` | `regression-triage`, `root-cause`, `waveform-debug`, `rtl-trace`, `add-debug-points` |
| `debug_agent/` | Python tools (standard library only) the agent calls |
| `dv/sva/` | Debug points attached with `bind`, no RTL edits: APB protocol checker on the SoC bus and every peripheral port, address-decode checker |
| `dv/tb/` | Directed SV testbench for `soc_top`, UVM-format messages |
| `dv/scripts/` | Verilator build/run of one test or a regression |
| `examples/` | Real outputs and `known_issues.md` (root-caused bugs) |

## Quick start

```sh
git clone https://github.com/bhaskar12pr/SOC_VERIF ../SOC_VERIF     # or set SOC_VERIF=/path
dv/scripts/run_regression.sh 10          # needs Verilator 5.x
python3 -m debug_agent triage runs/
python3 -m debug_agent evidence runs/random_rw_s3
```

Then in Claude Code, from this directory: *"use the soc-debug agent to debug the regression in runs/"*.

## Tools

```
python3 -m debug_agent triage   <runs_dir>            # group failures by first-failure signature
python3 -m debug_agent first    <log>                 # first failure + log context
python3 -m debug_agent evidence <run_dir> [--signals GLOB]   # evidence pack for one run
python3 -m debug_agent wave     <vcd> --signals GLOB --from PS --to PS
python3 -m debug_agent signals  <vcd> PATTERN
python3 -m debug_agent drivers  soc_top.u_apb_spi_master.PREADY   # traces through sub-module ports
python3 -m debug_agent hier     soc_top
```

- **Log parser:** UVM report format, Verilator, Questa, VCS and Xcelium assertion/error
  formats, plus `[DBG][CATEGORY][instance]` debug-point messages. The Verilator
  formats are tested on real logs; the Questa, VCS and Xcelium fixtures are
  hand-written samples of those formats and should be checked against your
  tools' real output.
- **First failure, not last:** the earliest error by sim time is the lead
  suspect; timeouts and fatals that follow are reported as symptoms.
- **VCD reader:** streams only the requested signals; rows only when a
  non-clock signal changes. FSDB: convert the needed scope/window with `fsdb2vcd`.
- **RTL tracer:** follows port connections into child instances, e.g.
  `soc_top.u_apb_spi_master.PREADY` -> `u_axiregs` -> `assign PREADY = 1'b1;`
  in `spi_master_apb_if.sv`. That's the hierarchy trace coverage_agent's
  scanner lacks.

## What it found on SOC_VERIF (real results)

Regression of 3 directed tests + 10 random seeds: **13 runs, 4 pass, 9 fail, 2 root causes**
(`examples/triage_report.md`):

1. **Unmapped address hangs the bus** (8 runs): `apb_node` holds
   `pready_o = 0` when no slave matches (`apb_node.sv:65`); there is no
   default/error slave. Integration gap. The decode checker flags it on the
   SETUP cycle; the TB timeout comes 66 cycles later.
2. **Free-running counter read back as a plain register** (1 run): test
   expectation bug; `TIMER` counts every cycle while enabled (`timer.sv:81`).

A third bug, in the testbench itself (APB read data sampled after the clock
edge), was found by comparing the TB's reads with the checker's
`SIM_DEBUG=1` transaction trace, and fixed. Details are in `examples/known_issues.md`.

## Tests

```sh
python3 -m pytest -q
```

## Limits

- RTL indexing is regex-based: macros, generate-for instance arrays,
  interfaces and structs can be missed (the tools say so, and the skills fall back to grep).
- The TB is directed SV, not UVM (Verilator can't run the UVM library). The
  tools parse real UVM logs from commercial simulators the same way.
- `run_sim.sh` targets Verilator; for VCS/Xcelium/Questa, swap the build/run
  lines. Everything downstream only needs `sim.log` and `waves.vcd`.
