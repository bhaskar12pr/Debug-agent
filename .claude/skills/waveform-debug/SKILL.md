---
name: waveform-debug
description: Query a VCD waveform around a failure time to confirm or reject a hypothesis - signal values, handshakes, when something changed. Use instead of opening a full waveform; works on large dumps.
---
# Waveform debug

```
python3 -m debug_agent signals runs/<run>/waves.vcd '<glob or substring>'   # find exact paths
python3 -m debug_agent wave runs/<run>/waves.vcd --signals 'TOP.tb_soc_top.dut.u_apb_timer.P*' \
        --signals '*timer_i.regs_q' --from 100000 --to 160000                  # times in ps
```

- Start with a narrow window: about 20 cycles before the first failure, 5 after.
- Rows appear only when a non-clock signal changes; signals that never change
  are listed under "unchanged in window" (a stuck signal is itself evidence).
- A bound checker's own ports (`...u_chk_*.<port>`) are exactly what its
  assertion saw: query those first.
- `'bxxxx` means X/Z. Find where the X starts and trace its driver with rtl-trace.
- Glob `*` matches across hierarchy dots; anchor with a full prefix to keep it small.
- FSDB: convert only the needed scope/window first (Verdi `fsdb2vcd -s <scope> -bt -et`).
