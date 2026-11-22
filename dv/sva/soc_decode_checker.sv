// soc_decode_checker.sv — checks the apb_node address decode inside soc_top.
//
// apb_node drives pready_o = 0 when no slave matches the address, so an
// access outside the address map hangs the bus forever. This checker reports
// that on the first cycle of the access instead of waiting for a timeout.
module soc_decode_checker #(
  parameter int unsigned NB_SLAVE = 4,
  parameter int unsigned ADDR_W   = 32
) (
  input logic                clk,
  input logic                rst_n,
  input logic                psel,
  input logic [ADDR_W-1:0]   paddr,
  input logic [NB_SLAVE-1:0] slave_sel
);
  // Checked in the SETUP phase only, so one bad access gives one message.
  a_addr_mapped: assert property (@(posedge clk) disable iff (!rst_n)
      $rose(psel) |-> (slave_sel != '0))
    else $error("[DBG][DECODE][soc_top.u_apb_node] unmapped address=0x%0h matches no slave; apb_node holds pready_o=0 (bus will hang)", paddr);

  a_single_slave: assert property (@(posedge clk) disable iff (!rst_n)
      $onehot0(slave_sel))
    else $error("[DBG][DECODE][soc_top.u_apb_node] overlapping address map address=0x%0h slave_sel=%b", paddr, slave_sel);
endmodule
