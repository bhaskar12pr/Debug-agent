---
name: add-debug-points
description: Recommend or write non-intrusive debug points - bound SVA checkers, [DBG] trace messages, waveform scoping - when a failure cannot be root-caused with the current visibility. Use when evidence is missing or a class of bug keeps recurring.
---
# Add debug points

Prefer, in this order (least intrusive first):

1. **Bound SVA checker** (`dv/sva/*.sv` + a `bind` line in `dv/sva/soc_binds.sv`).
   No RTL edit. Reuse `apb_protocol_checker` for any APB port; write a new
   checker module for other protocols.
2. **`ifdef SIM_DEBUG` trace** in a checker (see the transaction trace in
   `apb_protocol_checker.sv`), enabled with `SIM_DEBUG=1 dv/scripts/run_sim.sh ...`.
3. **RTL-internal `ifdef SIM_DEBUG` `$display`**: only with the RTL owner's approval.
4. **Synthesizable debug** (sticky error bits, counters, debug bus): design decision, propose only.

## Message format (required, the parser depends on it)
```
$error("[DBG][<CATEGORY>][<instance path>] <event> key=value ...");
```
- CATEGORY: APB, DECODE, FIFO, FSM, CDC, RESET, ... (short, upper case)
- instance path: hierarchical path from the SoC top (`soc_top.u_apb_uart`), which
  `evidence` resolves to an RTL file.
- Report once per event (use `$rose(...)` or a SETUP-phase antecedent), not
  every cycle: a flooding checker hides the next failure.

## Where checkers pay off most
Valid/ready and APB handshakes, address decode/unmapped access, FIFO
overflow/underflow, FSM illegal/stuck state, X on control after reset,
CDC handshakes, interrupt set/clear.

Always build and rerun one passing and one failing test after adding a checker
to show it fires only on the bug.
