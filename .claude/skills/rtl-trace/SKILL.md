---
name: rtl-trace
description: Find which RTL file/line drives a signal, following port connections down through sub-module instances, and map hierarchical paths to source files. Use when a failure names an instance or signal and you need the code behind it.
---
# RTL trace

```
python3 -m debug_agent hier soc_top                              # instance tree with files
python3 -m debug_agent drivers soc_top.u_apb_spi_master.PREADY  # traces into u_axiregs
```

- Paths may start with simulator prefixes (`TOP.tb_soc_top.dut...`); the first
  known module name anchors the lookup.
- Driver kinds: `tie-off` (constant assign), `assign`, `procedural`
  (always_comb/ff; read the surrounding if/case for the condition), `port`
  (driven by a child instance; the child's drivers follow on the next lines).
- After finding the driver line, `Read` about 30 lines around it to get the
  condition under which it takes the failing value.
- Backend: with pyslang installed (`## RTL (pyslang)` in evidence packs) lookups
  are on the elaborated design: macros, parameters and generate instances
  (`u_apb_timer.TIMER_GEN[0].timer_i`) are exact. Without it the regex indexer
  is used, which misses generate-loop instances, macros and interfaces/structs;
  if it finds nothing, fall back to `Grep -n '<signal>'` in the module's file.
- `hier` with pyslang shows each instance's resolved parameters: check them
  when behavior depends on a depth/width/count.
- `python3 -m debug_agent lint --errors` before trusting a new RTL/TB drop:
  compile errors (missing module, port mismatch, reserved word) explain many
  "sim won't start" and X-propagation failures.
- RTL defaults: `$SOC_VERIF/rtl` and `dv/` (checkers, TB). Override with `--rtl DIR` (repeatable).
