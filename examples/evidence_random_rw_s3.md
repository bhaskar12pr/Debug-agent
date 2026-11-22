# Evidence pack: `random_rw_s3`

- log: `runs/random_rw_s3/sim.log`
- failures: 3 total, 3 distinct

## First failure (most likely the cause; later ones are often symptoms)

- time: 195000
- severity/source: ERROR / sva
- scope: `TOP.tb_soc_top.dut.u_chk_decode.a_addr_mapped`  id: `a_addr_mapped`
- message: [DBG][DECODE][soc_top.u_apb_node] unmapped address=0x10004024 matches no slave; apb_node holds pready_o=0 (bus will hang)
- reported at: `soc_decode_checker.sv:19`

## Failure timeline (deduplicated)

| first at | severity | source | scope | message | count |
|---|---|---|---|---|---|
| 195000 | ERROR | sva | `TOP.tb_soc_top.dut.u_chk_decode.a_addr_mapped` | [DBG][DECODE][soc_top.u_apb_node] unmapped address=0x10004024 matches no slave; apb_node holds pready_o=0 (bus will hang) | 1 |
| 515000 | ERROR | sva | `TOP.tb_soc_top.dut.u_chk_bus` | [DBG][APB][soc_top.bus] stall no PREADY for 32 cycles addr=0x10004024 write=0 | 1 |
| 845000 | FATAL | uvm | `uvm_test_top` | no PREADY after 64 cycles: READ addr=0x10004024 | 1 |

## Log context

```
     1  UVM_INFO dv/tb/tb_soc_top.sv(125) @ 0: uvm_test_top [TEST] starting test=random_rw seed=3
     2  UVM_INFO dv/tb/tb_soc_top.sv(104) @ 85000: uvm_test_top [APB_RD] addr=0x1000203c data=0x00000000
     3  UVM_INFO dv/tb/tb_soc_top.sv(104) @ 115000: uvm_test_top [APB_RD] addr=0x10002014 data=0x00000000
     4  UVM_INFO dv/tb/tb_soc_top.sv(104) @ 145000: uvm_test_top [APB_RD] addr=0x1000101c data=0x00000000
     5  UVM_INFO dv/tb/tb_soc_top.sv(104) @ 175000: uvm_test_top [APB_RD] addr=0x10003034 data=0x00000000
     6> [195000] %Error: soc_decode_checker.sv:19: Assertion failed in TOP.tb_soc_top.dut.u_chk_decode.a_addr_mapped: [DBG][DECODE][soc_top.u_apb_node] unmapped address=0x10004024 matches no slave; apb_node holds pready_o=0 (bus will hang)
     7  -Info: dv/sva/soc_decode_checker.sv:19: Verilog $stop, ignored due to +verilator+error+limit
     8  [515000] %Error: apb_protocol_checker.sv:51: Assertion failed in TOP.tb_soc_top.dut.u_chk_bus: [DBG][APB][soc_top.bus] stall no PREADY for 32 cycles addr=0x10004024 write=0
     9  -Info: dv/sva/apb_protocol_checker.sv:51: Verilog $stop, ignored due to +verilator+error+limit
    10  UVM_FATAL dv/tb/tb_soc_top.sv(88) @ 845000: uvm_test_top [APB_TIMEOUT] no PREADY after 64 cycles: READ addr=0x10004024
    11  --- UVM Report Summary ---
    12  UVM_ERROR : 0
    13  UVM_FATAL : 1
    14  TEST random_rw SEED 3 FAILED
    15  - dv/tb/tb_soc_top.sv:70: Verilog $finish
```

## Waveform window 0..245000 ps

```
time(ps) | rst_n | psel |      paddr | slave_sel
       0 |     0 |    0 | 0x00000000 |       0x0
   45000 |     1 |    0 | 0x00000000 |       0x0
   65000 |     1 |    1 | 0x1000203c |       0x4
   85000 |     1 |    0 | 0x1000203c |       0x0
   95000 |     1 |    1 | 0x10002014 |       0x4
  115000 |     1 |    0 | 0x10002014 |       0x0
  125000 |     1 |    1 | 0x1000101c |       0x2
  145000 |     1 |    0 | 0x1000101c |       0x0
  155000 |     1 |    1 | 0x10003034 |       0x8
  175000 |     1 |    0 | 0x10003034 |       0x0
  185000 |     1 |    1 | 0x10004024 |       0x0
signals:
  rst_n = TOP.tb_soc_top.dut.u_chk_decode.rst_n
  psel = TOP.tb_soc_top.dut.u_chk_decode.psel
  paddr = TOP.tb_soc_top.dut.u_chk_decode.paddr
  slave_sel = TOP.tb_soc_top.dut.u_chk_decode.slave_sel
unchanged in window:
  TOP.tb_soc_top.dut.u_chk_decode.NB_SLAVE = 0x00000004
  TOP.tb_soc_top.dut.u_chk_decode.ADDR_W = 0x00000020
```

## RTL

- `soc_top.u_apb_node` is module `apb_node` in `SOC_VERIF/rtl/ip/apb_node/apb_node.sv:20`
  - `soc_top.u_apb_node.pready_o` driven at `SOC_VERIF/rtl/ip/apb_node/apb_node.sv:65` (procedural): `pready_o  = 1'b0;`
  - `soc_top.u_apb_node.pready_o` driven at `SOC_VERIF/rtl/ip/apb_node/apb_node.sv:78` (procedural): `pready_o     = pready_i[i];`
