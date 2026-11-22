// soc_binds.sv — attaches the debug checkers to SOC_VERIF's soc_top.
// Compile this file with the RTL; nothing in rtl/ is modified.

// Upstream (SoC-level) APB bus.
bind soc_top apb_protocol_checker #(.NAME("soc_top.bus")) u_chk_bus (
  .clk(clk_i), .rst_n(rst_ni), .psel(psel_i), .penable(penable_i), .pwrite(pwrite_i),
  .paddr(paddr_i), .pwdata(pwdata_i), .prdata(prdata_o), .pready(pready_o), .pslverr(pslverr_o));

// Address decode in apb_node.
bind soc_top soc_decode_checker #(.NB_SLAVE(NB_MASTER)) u_chk_decode (
  .clk(clk_i), .rst_n(rst_ni), .psel(psel_i), .paddr(paddr_i), .slave_sel(m_psel));

// One checker per peripheral port (slave side of apb_node).
bind soc_top apb_protocol_checker #(.ADDR_W(12), .NAME("soc_top.u_apb_gpio")) u_chk_gpio (
  .clk(clk_i), .rst_n(rst_ni), .psel(m_psel[0]), .penable(m_penable[0]), .pwrite(m_pwrite[0]),
  .paddr(m_paddr[0][11:0]), .pwdata(m_pwdata[0]), .prdata(m_prdata[0]), .pready(m_pready[0]), .pslverr(m_pslverr[0]));
bind soc_top apb_protocol_checker #(.ADDR_W(12), .NAME("soc_top.u_apb_uart")) u_chk_uart (
  .clk(clk_i), .rst_n(rst_ni), .psel(m_psel[1]), .penable(m_penable[1]), .pwrite(m_pwrite[1]),
  .paddr(m_paddr[1][11:0]), .pwdata(m_pwdata[1]), .prdata(m_prdata[1]), .pready(m_pready[1]), .pslverr(m_pslverr[1]));
bind soc_top apb_protocol_checker #(.ADDR_W(12), .NAME("soc_top.u_apb_timer")) u_chk_timer (
  .clk(clk_i), .rst_n(rst_ni), .psel(m_psel[2]), .penable(m_penable[2]), .pwrite(m_pwrite[2]),
  .paddr(m_paddr[2][11:0]), .pwdata(m_pwdata[2]), .prdata(m_prdata[2]), .pready(m_pready[2]), .pslverr(m_pslverr[2]));
bind soc_top apb_protocol_checker #(.ADDR_W(12), .NAME("soc_top.u_apb_spi_master")) u_chk_spi (
  .clk(clk_i), .rst_n(rst_ni), .psel(m_psel[3]), .penable(m_penable[3]), .pwrite(m_pwrite[3]),
  .paddr(m_paddr[3][11:0]), .pwdata(m_pwdata[3]), .prdata(m_prdata[3]), .pready(m_pready[3]), .pslverr(m_pslverr[3]));
