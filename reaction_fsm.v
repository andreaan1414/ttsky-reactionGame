`default_nettype none

// Allow Makefile to override timing parameters for fast simulation.
// e.g.:  iverilog -DTICK_PERIOD=100 -DWAIT_BLINK_PER=200 -DFLASH_HALF=200
`ifdef TICK_PERIOD
  `define _TICK      `TICK_PERIOD
`else
  `define _TICK      2_500_000
`endif
`ifdef WAIT_BLINK_PER
  `define _BLINK     `WAIT_BLINK_PER
`else
  `define _BLINK     12_500_000
`endif
`ifdef FLASH_HALF
  `define _FLASH     `FLASH_HALF
`else
  `define _FLASH     12_500_000
`endif

module reaction_game #(
    parameter CLK_FREQ       = 25_000_000,
    parameter TICK_PERIOD    = `_TICK,
    parameter WAIT_BLINK_PER = `_BLINK,
    parameter FLASH_HALF     = `_FLASH
) (
    input  wire clk,
    input  wire rst,
    input  wire go_btn,
    input  wire react_btn,
    output wire [7:0] leds
);

 // states 
    localparam [1:0]
        S_IDLE = 2'd0,
        S_WAIT = 2'd1,
        S_REACT = 2'd2,
        S_DISPLAY = 2'd3;

    reg [1:0] state, next_state;

    wire [5:0] lfsr_Q;
    wire [7:0] lfsr_rnd;

    lfsr lfsr_inst (
        .clk (clk),
        .rst (rst),
        .rnd (lfsr_rnd),
        .Q   (lfsr_Q)
    );

    reg [5:0] rand_wait;   // latched delay value
    reg [5:0] wait_cnt;    // counts down to 0
    wire      wait_done = (wait_cnt == 6'd0);


    reg [24:0] prescaler;
    wire       tick = (prescaler == TICK_PERIOD - 1);

    always @(posedge clk) begin
        if (rst || state == S_IDLE)
            prescaler <= 25'd0;
        else if (tick)
            prescaler <= 25'd0;
        else
            prescaler <= prescaler + 1'b1;
    end

   
    wire [4:0] react_time_Q;
    wire       react_UTC;

    countUD5L react_counter (
        .clkin (clk),
        .rst   (rst),
        .UP    (tick & (state == S_REACT)),
        .DW    (1'b0),
        .LD    (state == S_IDLE),   // clear to 0 while idle
        .Din   (5'b0),
        .Q     (react_time_Q),
        .UTC   (react_UTC),
        .DTC   ()
    );

    
    always @(posedge clk) begin
        if (rst) begin
            rand_wait <= 6'd0;
            wait_cnt  <= 6'd0;
        end else if (state == S_IDLE && go_btn) begin
            // Clamp minimum to 5 ticks (500ms) to avoid instant trigger
            rand_wait <= (lfsr_Q == 6'd0) ? 6'd5 : lfsr_Q;
            wait_cnt  <= (lfsr_Q == 6'd0) ? 6'd5 : lfsr_Q;
        end else if (state == S_WAIT && tick && !wait_done) begin
            wait_cnt <= wait_cnt - 1'b1;
        end
    end

    
    reg [24:0] blink_cnt;
    reg        blink_state;

    always @(posedge clk) begin
        if (rst || state != S_WAIT) begin
            blink_cnt   <= 25'd0;
            blink_state <= 1'b0;
        end else if (blink_cnt == WAIT_BLINK_PER - 1) begin
            blink_cnt   <= 25'd0;
            blink_state <= ~blink_state;
        end else begin
            blink_cnt <= blink_cnt + 1'b1;
        end
    end

  
    wire flash_out;

    flash_ctrl #(
        .HALF_PERIOD(FLASH_HALF)
    ) flash_inst (
        .clk      (clk),
        .rst      (rst),
        .enable   (state == S_DISPLAY),
        .flash_out(flash_out)
    );


    always @(posedge clk) begin
        if (rst)
            state <= S_IDLE;
        else
            state <= next_state;
    end

  // next state logic 
    always @(*) begin
        next_state = state;
        case (state)
            S_IDLE:    if (go_btn)                  next_state = S_WAIT;
            S_WAIT:    if (wait_done && tick)        next_state = S_REACT;
            S_REACT:   if (react_btn || react_UTC)   next_state = S_DISPLAY;
            S_DISPLAY: if (rst)                      next_state = S_IDLE;
            default:                                 next_state = S_IDLE;
        endcase
    end

  // led output 
    reg [7:0] led_r;
    always @(*) begin
        case (state)
            S_IDLE:    led_r = 8'h00;
            S_WAIT:    led_r = {7'b000_0000, blink_state};
            S_REACT:   led_r = 8'h80;
            S_DISPLAY: led_r = {3'b000, react_time_Q} ^ {8{flash_out}};
            default:   led_r = 8'h00;
        endcase
    end

    assign leds = led_r;

endmodule
