---
name: root-cause
description: Root-cause one failing simulation run from its evidence pack - first failure, log, waveform, RTL - and classify it as RTL, TB, stimulus, spec or tool. Use for any single failing run, assertion failure, scoreboard mismatch, timeout or hang.
---
# Root-cause one failing run

```
python3 -m debug_agent evidence runs/<test>_s<seed>        # add --signals 'GLOB' for more waves
```

## Reasoning rules
1. **First failure wins.** The earliest error by sim time is the lead suspect.
   Timeouts, watchdogs and `UVM_FATAL`s that come later are usually symptoms.
2. **Name the mechanism, not the symptom.** "Bus hung" is a symptom;
   "apb_node drives pready_o=0 when no slave matches, apb_node.sv:65" is a cause.
3. **Every claim needs a pointer**: log `file:line`, a signal value at a time,
   or RTL `file:line`. No pointer, no claim.
4. **Decide who is wrong: the design, the checker or the expectation.**
   - Scoreboard/readback mismatch: is the register volatile (counter, status,
     W1C, read-clear)? Check the RTL write/next-state logic before blaming RTL.
   - Assertion failure: check the assertion's antecedent matches the spec;
     checkers have bugs too.
   - Timeout/hang: find who should have responded and why they did not
     (decode, clock/reset, handshake, FIFO full).
5. **Look for the bucket's common factor** (same address range, same register,
   same phase) across 2-3 runs in the bucket before generalizing.

## Classification guide
| Class | Typical evidence |
|---|---|
| RTL bug | design output violates spec/protocol while inputs are legal |
| TB/checker bug | design behavior matches spec; the model, expectation or assertion is wrong |
| Stimulus/test bug | the test drove something illegal or outside the supported config |
| Spec/integration gap | each block is fine alone; the combination (address map, tie-offs, params) is not |
| Tool/env | crash, license, compile-order, X from uninitialized TB, missing file |

## Verify
- Rerun the same seed with `SIM_DEBUG=1 dv/scripts/run_sim.sh <test> <seed>` for a [DBG] transaction trace.
- For a TB-expectation hypothesis, show the waveform proving the design behaved per spec.
- Write the report in the format in `.claude/agents/soc-debug.md`.
