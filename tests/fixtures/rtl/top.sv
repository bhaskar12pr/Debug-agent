// top -> u_mid (mid) -> u_leaf (leaf): `ready` is tied off two levels down.
module top (input logic clk, output logic ready, output logic busy);
  mid u_mid (.clk(clk), .ready(ready));
  always_comb begin
    busy = 1'b0;   // procedural driver
  end
endmodule

module mid (input logic clk, output logic ready);
  leaf #(.W(4)) u_leaf (
    .clk   (clk),
    .rdy_o (ready)
  );
endmodule

module leaf #(parameter int W = 8) (input logic clk, output logic rdy_o);
  assign rdy_o = 1'b1;
endmodule
