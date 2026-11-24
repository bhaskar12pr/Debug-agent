// gen_top -> GEN[0..1].u_cell (ok_cell): instances created by a generate loop,
// which the regex indexer cannot see; plus a macro-defined tie-off value.
`define ONE 1'b1
module gen_top #(parameter int N = 2) (output logic [N-1:0] ok);
  for (genvar g = 0; g < N; g++) begin : GEN
    ok_cell u_cell (.ok_o(ok[g]));
  end
endmodule

module ok_cell (output logic ok_o);
  assign ok_o = `ONE;
endmodule
