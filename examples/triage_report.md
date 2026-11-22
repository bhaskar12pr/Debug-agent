# Regression triage

13 runs, 4 passed, 9 failed, 2 distinct first-failure signature(s)

## Bucket 1: 8 run(s)

- signature: `ERROR|DBG:DECODE:soc_top.u_apb_node|[DBG][DECODE][soc_top.u_apb_node] unmapped address=0x<HEX> matches no slave; apb_node holds pready_o=<N> (bus will hang)`
- runs: random_rw_s1, random_rw_s10, random_rw_s2, random_rw_s3, random_rw_s5, random_rw_s6, random_rw_s7, random_rw_s8
- first failure (example `random_rw_s1` @ 75000): ERROR [TOP.tb_soc_top.dut.u_chk_decode.a_addr_mapped] [DBG][DECODE][soc_top.u_apb_node] unmapped address=0x1000403c matches no slave; apb_node holds pready_o=0 (bus will hang)
- log: `runs/random_rw_s1/sim.log:2`

## Bucket 2: 1 run(s)

- signature: `ERROR|SCB_MISMATCH|TIMER0.TIMER addr=0x<HEX> exp=0x<HEX> got=0x<HEX>`
- runs: timer_count_s1
- first failure (example `timer_count_s1` @ 145000): ERROR [uvm_test_top] TIMER0.TIMER addr=0x10002000 exp=0x00000100 got=0x00000102
- log: `runs/timer_count_s1/sim.log:5`

