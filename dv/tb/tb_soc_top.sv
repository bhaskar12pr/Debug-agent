// tb_soc_top.sv — directed SystemVerilog testbench for SOC_VERIF's soc_top.
//
// Not UVM (Verilator 5.0x cannot run the UVM library), but every message
// uses the UVM report format so the debug agent's parsers treat these logs
// exactly like real UVM logs:
//   UVM_INFO|UVM_WARNING|UVM_ERROR|UVM_FATAL <file>(<line>) @ <time>: <reporter> [<ID>] <msg>
//
// Tests (+TEST=<name>, +SEED=<n>):
//   gpio_rw       write/readback GPIO PADDIR + PADOUT, check gpio_out pins
//   timer_cmp_rw  write/readback timer0 CMP register
//   timer_count   enable timer0, then write/readback the TIMER count register
//   random_rw     seeded random reads across 0x1000_0000..0x1000_4FFF
`timescale 1ns/1ps

`define TB_MSG(SEV, ID, MSG) \
  $display("%s %s(%0d) @ %0t: %s [%s] %s", SEV, `__FILE__, `__LINE__, $time, "uvm_test_top", ID, MSG)
`define TB_INFO(ID, MSG)  begin `TB_MSG("UVM_INFO", ID, MSG); end
`define TB_ERROR(ID, MSG) begin `TB_MSG("UVM_ERROR", ID, MSG); n_errors++; end
`define TB_FATAL(ID, MSG) begin `TB_MSG("UVM_FATAL", ID, MSG); n_fatals++; report_and_finish(); end

module tb_soc_top;
  localparam int unsigned TIMEOUT_CYCLES = 64;

  logic clk = 0, rst_n = 0;
  always #5 clk = ~clk;

  logic        psel = 0, penable = 0, pwrite = 0;
  logic [31:0] paddr = '0, pwdata = '0, prdata;
  logic        pready, pslverr;

  logic [31:0] gpio_out, gpio_dir;
  logic        gpio_irq, uart_tx, uart_event;
  logic [3:0]  timer_irq;
  logic [1:0]  spi_events, spi_mode;
  logic        spi_clk, spi_csn0, spi_csn1, spi_csn2, spi_csn3;
  logic        spi_sdo0, spi_sdo1, spi_sdo2, spi_sdo3;

  soc_top dut (
    .clk_i(clk), .rst_ni(rst_n),
    .penable_i(penable), .pwrite_i(pwrite), .paddr_i(paddr), .psel_i(psel),
    .pwdata_i(pwdata), .prdata_o(prdata), .pready_o(pready), .pslverr_o(pslverr),
    .gpio_in(32'h0), .gpio_out(gpio_out), .gpio_dir(gpio_dir), .gpio_irq_o(gpio_irq),
    .uart_rx_i(1'b1), .uart_tx_o(uart_tx), .uart_event_o(uart_event),
    .timer_irq_o(timer_irq),
    .spi_events_o(spi_events), .spi_clk(spi_clk),
    .spi_csn0(spi_csn0), .spi_csn1(spi_csn1), .spi_csn2(spi_csn2), .spi_csn3(spi_csn3),
    .spi_mode(spi_mode),
    .spi_sdo0(spi_sdo0), .spi_sdo1(spi_sdo1), .spi_sdo2(spi_sdo2), .spi_sdo3(spi_sdo3),
    .spi_sdi0(1'b0), .spi_sdi1(1'b0), .spi_sdi2(1'b0), .spi_sdi3(1'b0)
  );

  // Sample slave outputs the way an APB master does: at the rising edge,
  // with pre-edge values (#1step). Sampling after @(posedge clk) instead reads
  // values that already changed on that edge, e.g. a free-running counter.
  clocking cb @(posedge clk);
    default input #1step;
    input pready, prdata, pslverr;
  endclocking

  int    n_errors = 0, n_fatals = 0;
  string test_name;
  int    seed = 1;

  task automatic report_and_finish();
    $display("--- UVM Report Summary ---");
    $display("UVM_ERROR : %0d", n_errors);
    $display("UVM_FATAL : %0d", n_fatals);
    if (n_errors == 0 && n_fatals == 0) $display("TEST %s SEED %0d PASSED", test_name, seed);
    else                                $display("TEST %s SEED %0d FAILED", test_name, seed);
    $finish;
  endtask

  // APB master: SETUP phase, then ACCESS phase until PREADY, with a watchdog.
  task automatic apb_xfer(input bit write, input logic [31:0] addr,
                          input logic [31:0] wdata, output logic [31:0] rdata);
    int cycles = 0;
    string op;
    if (write) op = "WRITE"; else op = "READ";
    @(cb);
    psel <= 1; penable <= 0; pwrite <= write; paddr <= addr; pwdata <= wdata;
    @(cb);
    penable <= 1;
    do begin
      @(cb);
      cycles++;
      if (cycles > TIMEOUT_CYCLES)
        `TB_FATAL("APB_TIMEOUT", $sformatf("no PREADY after %0d cycles: %s addr=0x%08h",
                  TIMEOUT_CYCLES, op, addr))
    end while (!cb.pready);
    rdata = cb.prdata;
    if (cb.pslverr)
      `TB_ERROR("APB_SLVERR", $sformatf("PSLVERR on %s addr=0x%08h", op, addr))
    psel <= 0; penable <= 0;
  endtask

  task automatic apb_write(input logic [31:0] addr, input logic [31:0] data);
    logic [31:0] unused;
    apb_xfer(1, addr, data, unused);
    `TB_INFO("APB_WR", $sformatf("addr=0x%08h data=0x%08h", addr, data))
  endtask

  task automatic apb_read(input logic [31:0] addr, output logic [31:0] data);
    apb_xfer(0, addr, '0, data);
    `TB_INFO("APB_RD", $sformatf("addr=0x%08h data=0x%08h", addr, data))
  endtask

  task automatic check_rw(input string reg_name, input logic [31:0] addr, input logic [31:0] data);
    logic [31:0] got;
    apb_write(addr, data);
    apb_read(addr, got);
    if (got !== data)
      `TB_ERROR("SCB_MISMATCH", $sformatf("%s addr=0x%08h exp=0x%08h got=0x%08h", reg_name, addr, data, got))
  endtask

  localparam logic [31:0] GPIO  = 32'h1000_0000;
  localparam logic [31:0] UART  = 32'h1000_1000;
  localparam logic [31:0] TIMER = 32'h1000_2000;
  localparam logic [31:0] SPI   = 32'h1000_3000;

  initial begin
    logic [31:0] rd, addr;
    if (!$value$plusargs("TEST=%s", test_name)) test_name = "gpio_rw";
    void'($value$plusargs("SEED=%d", seed));
    void'($urandom(seed));
    `TB_INFO("TEST", $sformatf("starting test=%s seed=%0d", test_name, seed))

    repeat (5) @(posedge clk);
    rst_n = 1;
    repeat (2) @(posedge clk);

    case (test_name)
      "gpio_rw": begin
        check_rw("GPIO.PADDIR", GPIO + 'h00, 32'hA5A5_5A5A);
        check_rw("GPIO.PADOUT", GPIO + 'h0C, 32'h0000_00F0);
        @(posedge clk);
        if (gpio_out !== 32'h0000_00F0)
          `TB_ERROR("PIN_MISMATCH", $sformatf("gpio_out exp=0x000000f0 got=0x%08h", gpio_out))
      end
      "timer_cmp_rw": begin
        check_rw("TIMER0.CMP", TIMER + 'h08, 32'h0000_1234);
      end
      "timer_count": begin
        apb_write(TIMER + 'h04, 32'h1);                 // CTRL.enable = 1, prescaler = 0
        check_rw("TIMER0.TIMER", TIMER + 'h00, 32'h0000_0100);
      end
      "random_rw": begin
        for (int k = 0; k < 8; k++) begin
          addr = 32'h1000_0000 + ({$urandom_range(0, 4)} << 12) + ({$urandom_range(0, 15)} << 2);
          apb_read(addr, rd);
        end
      end
      default: `TB_FATAL("TEST", $sformatf("unknown test '%s'", test_name))
    endcase

    repeat (5) @(posedge clk);
    report_and_finish();
  end

  initial begin
    if ($test$plusargs("WAVES")) begin
      $dumpfile("waves.vcd");
      $dumpvars(0, tb_soc_top);
    end
  end
endmodule
