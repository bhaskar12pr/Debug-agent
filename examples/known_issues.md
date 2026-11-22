# Known issues (agent knowledge base)

Root-caused failures with their evidence. The soc-debug agent checks new
buckets against this file first. Add an entry for every bug you close:
signature, root cause, evidence, fix. These also serve as regression tests
for the agent's own diagnoses.

---

## KI-001: Unmapped APB address hangs the bus

- **Signature:** `ERROR|DBG:DECODE:soc_top.u_apb_node|... unmapped address=0x<HEX> matches no slave ...`
- **Seen in:** `random_rw` seeds 1,2,3,5,6,7,8,10 (any access to 0x1000_4000..0x1000_4FFF)
- **Root cause:** `apb_node` defaults `pready_o = 1'b0` and only overrides it
  for a matching slave (`SOC_VERIF/rtl/ip/apb_node/apb_node.sv:65`, `:78`).
  No slave matches outside the 4 x 4 KB map, so `pready_o` stays 0 forever and
  the master waits indefinitely. There is no default slave / error response.
- **Classification:** spec/integration gap. Each IP behaves as designed; the
  SoC integration has no handling for unmapped accesses. The test is also
  generating addresses outside the map (`random_rw` picks region 0..4).
- **Evidence:** first failure is the decode assertion at the SETUP phase
  (`soc_decode_checker.sv:19`); the bus stall checker fires 32 cycles later and
  the TB `APB_TIMEOUT` fatal 64 cycles later - both symptoms. Waveform:
  `psel=1, paddr=0x10004024, slave_sel=0x0`. See `examples/evidence_random_rw_s3.md`.
- **Fix options:** (RTL/integration owner) add a default slave in `soc_top`
  that returns `pready=1, pslverr=1` for unmapped addresses, per APB3 error
  response; (DV owner) until then, constrain `random_rw` to mapped regions
  and add a directed `unmapped_access` test that expects PSLVERR.

## KI-002: Readback of a free-running counter register

- **Signature:** `ERROR|SCB_MISMATCH|TIMER0.TIMER addr=0x<HEX> exp=0x<HEX> got=0x<HEX>`
- **Seen in:** `timer_count` seed 1
- **Root cause:** the test enables timer0 (`CTRL.enable=1`, prescaler 0) and then
  expects a write/readback of the `TIMER` count register to return the written
  value. In `timer.sv` the count register increments every cycle while enabled
  (`SOC_VERIF/rtl/ip/apb_timer/timer.sv:81-82`), so the read returns the
  written value plus the cycles elapsed (0x100 -> 0x102).
- **Classification:** TB/test bug (wrong expectation). The design matches its own spec.
- **Evidence:** waveform `timer_i.regs_q[TIMER]` = 0x100 at 115 ns, +1 every
  10 ns, `PRDATA=0x102` at the read's ACCESS edge (135 ns). See
  `examples/evidence_timer_count_s1.md`.
- **Fix:** (DV) treat `TIMER` as volatile in the register model: check
  `got - exp` is within the elapsed cycle count, or disable the timer before
  the readback.

## KI-003 (fixed): TB sampled APB read data after the clock edge

- **Symptom:** read data one cycle "ahead" of what the bus checker's
  transaction trace showed (TB got 0x103 where `[DBG][APB]` trace showed 0x102).
- **Root cause:** `apb_xfer` sampled `pready`/`prdata` after `@(posedge clk)`,
  i.e. post-edge values. An APB master samples at the edge (pre-edge values).
- **Found by:** comparing the TB's `APB_RD` message with the `SIM_DEBUG=1`
  checker trace for the same transfer - a good example of why independent
  debug points matter.
- **Fix (applied):** clocking block `cb` with `default input #1step` in
  `dv/tb/tb_soc_top.sv`, used for every wait in `apb_xfer` (mixing `@(cb)` and
  `@(posedge clk)` in one task resolves in the same timestep and reads stale data).
