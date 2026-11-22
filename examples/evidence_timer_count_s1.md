# Evidence pack: `timer_count_s1`

- log: `runs/timer_count_s1/sim.log`
- failures: 1 total, 1 distinct

## First failure (most likely the cause; later ones are often symptoms)

- time: 145000
- severity/source: ERROR / uvm
- scope: `uvm_test_top`  id: `SCB_MISMATCH`
- message: TIMER0.TIMER addr=0x10002000 exp=0x00000100 got=0x00000102
- reported at: `dv/tb/tb_soc_top.sv:112`

## Failure timeline (deduplicated)

| first at | severity | source | scope | message | count |
|---|---|---|---|---|---|
| 145000 | ERROR | uvm | `uvm_test_top` | TIMER0.TIMER addr=0x10002000 exp=0x00000100 got=0x00000102 | 1 |

## Log context

```
     1  UVM_INFO dv/tb/tb_soc_top.sv(125) @ 0: uvm_test_top [TEST] starting test=timer_count seed=1
     2  UVM_INFO dv/tb/tb_soc_top.sv(99) @ 85000: uvm_test_top [APB_WR] addr=0x10002004 data=0x00000001
     3  UVM_INFO dv/tb/tb_soc_top.sv(99) @ 115000: uvm_test_top [APB_WR] addr=0x10002000 data=0x00000100
     4  UVM_INFO dv/tb/tb_soc_top.sv(104) @ 145000: uvm_test_top [APB_RD] addr=0x10002000 data=0x00000102
     5> UVM_ERROR dv/tb/tb_soc_top.sv(112) @ 145000: uvm_test_top [SCB_MISMATCH] TIMER0.TIMER addr=0x10002000 exp=0x00000100 got=0x00000102
     6  --- UVM Report Summary ---
     7  UVM_ERROR : 1
     8  UVM_FATAL : 0
     9  TEST timer_count SEED 1 FAILED
    10  - dv/tb/tb_soc_top.sv:70: Verilog $finish
```

## Waveform window 0..195000 ps

```
time(ps) | PADDR |     PWDATA | PWRITE | PSEL | PENABLE |     PRDATA |                     regs_q
       0 | 0x000 | 0x00000000 |      0 |    0 |       0 | 0x00000000 | 0x000000000000000000000000
   65000 | 0x004 | 0x00000001 |      1 |    1 |       0 | 0x00000000 | 0x000000000000000000000000
   75000 | 0x004 | 0x00000001 |      1 |    1 |       1 | 0x00000000 | 0x000000000000000000000000
   85000 | 0x000 | 0x00000000 |      0 |    0 |       0 | 0x00000000 | 0x000000000000000100000000
   95000 | 0x000 | 0x00000100 |      1 |    1 |       0 | 0x00000000 | 0x000000010000000100000000
  105000 | 0x000 | 0x00000100 |      1 |    1 |       1 | 0x00000000 | 0x000000020000000100000000
  115000 | 0x000 | 0x00000000 |      0 |    0 |       0 | 0x00000000 | 0x000001000000000100000000
  125000 | 0x000 | 0x00000000 |      0 |    1 |       0 | 0x00000000 | 0x000001010000000100000000
  135000 | 0x000 | 0x00000000 |      0 |    1 |       1 | 0x00000102 | 0x000001020000000100000000
  145000 | 0x000 | 0x00000000 |      0 |    0 |       0 | 0x00000000 | 0x000001030000000100000000
  155000 | 0x000 | 0x00000000 |      0 |    0 |       0 | 0x00000000 | 0x000001040000000100000000
  165000 | 0x000 | 0x00000000 |      0 |    0 |       0 | 0x00000000 | 0x000001050000000100000000
  175000 | 0x000 | 0x00000000 |      0 |    0 |       0 | 0x00000000 | 0x000001060000000100000000
  185000 | 0x000 | 0x00000000 |      0 |    0 |       0 | 0x00000000 | 0x000001070000000100000000
  195000 | 0x000 | 0x00000000 |      0 |    0 |       0 | 0x00000000 | 0x000001080000000100000000
signals:
  PADDR = TOP.tb_soc_top.dut.u_apb_timer.PADDR
  PWDATA = TOP.tb_soc_top.dut.u_apb_timer.PWDATA
  PWRITE = TOP.tb_soc_top.dut.u_apb_timer.PWRITE
  PSEL = TOP.tb_soc_top.dut.u_apb_timer.PSEL
  PENABLE = TOP.tb_soc_top.dut.u_apb_timer.PENABLE
  PRDATA = TOP.tb_soc_top.dut.u_apb_timer.PRDATA
  regs_q = TOP.tb_soc_top.dut.u_apb_timer.TIMER_GEN[0].timer_i.regs_q
unchanged in window:
  TOP.tb_soc_top.dut.u_apb_timer.PREADY = 1
  TOP.tb_soc_top.dut.u_apb_timer.PSLVERR = 0
  TOP.tb_soc_top.dut.u_apb_timer.TIMER_GEN[1].timer_i.regs_q = 0x000000000000000000000000
```
