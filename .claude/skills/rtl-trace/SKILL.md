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
- The indexer is regex-based: macros, generate-for instance arrays and
  interfaces/structs may be missed. If it finds nothing, fall back to
  `Grep -n '<signal>'` in the module's file.
- RTL defaults: `$SOC_VERIF/rtl` and `dv/` (checkers, TB). Override with `--rtl DIR` (repeatable).
