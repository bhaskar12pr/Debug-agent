// apb_protocol_checker.sv — non-intrusive APB3 protocol checker.
//
// Attached to the design with `bind` (see soc_binds.sv), so the RTL is never
// edited. Every message uses one fixed, machine-parseable format:
//   [DBG][<CATEGORY>][<checker instance>] <event> key=value ...
// which the debug agent's log parser (debug_agent/logparse.py) understands.
module apb_protocol_checker #(
  parameter int unsigned ADDR_W        = 32,
  parameter int unsigned DATA_W        = 32,
  parameter int unsigned STALL_CYCLES  = 32,
  parameter string       NAME          = "apb"
) (
  input logic              clk,
  input logic              rst_n,
  input logic              psel,
  input logic              penable,
  input logic              pwrite,
  input logic [ADDR_W-1:0] paddr,
  input logic [DATA_W-1:0] pwdata,
  input logic [DATA_W-1:0] prdata,
  input logic              pready,
  input logic              pslverr
);
  // A transfer must start with a SETUP phase (PSEL high, PENABLE low).
  a_setup_first: assert property (@(posedge clk) disable iff (!rst_n)
      $rose(psel) |-> !penable)
    else $error("[DBG][APB][%s] protocol PENABLE high in first cycle of PSEL addr=0x%0h", NAME, paddr);

  // SETUP is followed by ACCESS on the next cycle.
  a_access_follows_setup: assert property (@(posedge clk) disable iff (!rst_n)
      (psel && !penable) |=> (psel && penable))
    else $error("[DBG][APB][%s] protocol ACCESS phase did not follow SETUP addr=0x%0h", NAME, $past(paddr));

  // PENABLE is only legal while PSEL is high.
  a_penable_needs_psel: assert property (@(posedge clk) disable iff (!rst_n)
      penable |-> psel)
    else $error("[DBG][APB][%s] protocol PENABLE without PSEL", NAME);

  // While waiting for PREADY, the master must hold address/control/data stable.
  a_stable_while_wait: assert property (@(posedge clk) disable iff (!rst_n)
      (psel && penable && !pready) |=> ($stable(paddr) && $stable(pwrite) && (!pwrite || $stable(pwdata))))
    else $error("[DBG][APB][%s] protocol signals changed while waiting for PREADY addr=0x%0h", NAME, paddr);

  // Stall watchdog: reports the hang at its source, long before a TB timeout.
  int unsigned wait_cycles;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) wait_cycles <= 0;
    else if (psel && penable && !pready) begin
      wait_cycles <= wait_cycles + 1;
      if (wait_cycles + 1 == STALL_CYCLES)
        $error("[DBG][APB][%s] stall no PREADY for %0d cycles addr=0x%0h write=%0d",
               NAME, STALL_CYCLES, paddr, pwrite);
    end else wait_cycles <= 0;
  end

`ifdef SIM_DEBUG
  // Transaction trace: one line per completed transfer.
  always_ff @(posedge clk)
    if (rst_n && psel && penable && pready)
      $display("[DBG][APB][%s] t=%0t xfer %s addr=0x%0h data=0x%0h pslverr=%0d", NAME, $time,
               pwrite ? "WRITE" : "READ", paddr, pwrite ? pwdata : prdata, pslverr);
`endif
endmodule
