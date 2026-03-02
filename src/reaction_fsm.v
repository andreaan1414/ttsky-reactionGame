/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 *
 * reaction_fsm.v 
 *
 * Game flow:
 *
 *   IDLE    rst_n released → start
 *           7-seg shows "–" (dash), all LEDs off
 *
 *   WAIT    Random LFSR delay counts down (500ms–6.3s)
 *           7-seg blinks "–" then one random LED (4–7) lights up 
 *           and player should press corresponding btn
 *
 *   REACT   Player presses the matching button (ui_in[7:4])
 *           If Wrong button is pressed fsm just waits till right one is pressed
 *           When Correct button pressed delay time in s will display
 *           Counter overflow is (3.1s)
 *
 *   DISPLAY Correct! All 4 LEDs flash together
 *           7-seg shows reaction time in tenths of seconds + decimal point
 
 * Pin connections:
 *  buttons 7,6,5,4
 *  LEDs 7,6,5,4
 *  seg_out[7:0] and dp 
 */
`default_nettype none

// Sim speed-up via Makefile -D flags
`ifdef TICK_PERIOD
  `define _TICK  `TICK_PERIOD
`else
  `define _TICK  2_500_000
`endif
`ifdef WAIT_BLINK_PER
  `define _BLINK `WAIT_BLINK_PER
`else
  `define _BLINK 12_500_000
`endif
`ifdef FLASH_HALF
  `define _FLASH `FLASH_HALF
`else
  `define _FLASH 12_500_000
`endif

module reaction_game #(
    parameter TICK_PERIOD    = `_TICK,
    parameter WAIT_BLINK_PER = `_BLINK,
    parameter FLASH_HALF     = `_FLASH
) (
    input  wire       clk,
    input  wire       rst,         
    input  wire [3:0] btn_in,      
    output reg  [3:0] led_out,      
    output wire [7:0] seg_out     
);

  // states 
    localparam [1:0] S_IDLE    = 2'd0,
                     S_WAIT    = 2'd1,
                     S_REACT   = 2'd2,
                     S_DISPLAY = 2'd3;

    reg [1:0] state, next_state;

    wire [5:0] lfsr_Q;
    wire [7:0] lfsr_rnd;

    lfsr lfsr_inst (
        .clk(clk), .rst(rst),
        .rnd(lfsr_rnd), .Q(lfsr_Q)
    );

   
    reg [1:0] target_idx;

    always @(posedge clk) begin
        if (rst)
            target_idx <= 2'd0;
        else if (state == S_WAIT && wait_done && tick)
            target_idx <= lfsr_rnd[1:0];
    end

    // One-hot  encoder
    wire [3:0] target_led;
    assign target_led = 4'b0001 << target_idx;

   
    wire correct_press = |(btn_in & target_led);


    wire flash_out;

    always @(*) begin
        case (state)
            S_IDLE:    led_out = 4'b0000;
            S_WAIT:    led_out = 4'b0000;
            S_REACT:   led_out = target_led;
            S_DISPLAY: led_out = flash_out ? 4'b1111 : 4'b0000;
            default:   led_out = 4'b0000;
        endcase
    end

  
    reg [5:0] rand_wait;
    reg [5:0] wait_cnt;
    wire      wait_done = (wait_cnt == 6'd0);

    always @(posedge clk) begin
        if (rst) begin
            rand_wait <= 6'd0;
            wait_cnt  <= 6'd0;
        end else if (state == S_IDLE && !rst) begin
            // Latch LFSR value as soon as we enter WAIT
            // (captured on the first cycle out of IDLE)
            rand_wait <= (lfsr_Q == 6'd0) ? 6'd5 : lfsr_Q;
            wait_cnt  <= (lfsr_Q == 6'd0) ? 6'd5 : lfsr_Q;
        end else if (state == S_WAIT && tick && !wait_done) begin
            wait_cnt <= wait_cnt - 1'b1;
        end
    end

   
    reg  [24:0] prescaler;
    wire        tick = (prescaler == TICK_PERIOD - 1);

    always @(posedge clk) begin
        if (rst || state == S_IDLE) prescaler <= 25'd0;
        else if (tick)              prescaler <= 25'd0;
        else                        prescaler <= prescaler + 1'b1;
    end

   
    wire [4:0] react_time_Q;
    wire       react_UTC;

    countUD5L react_counter (
        .clkin(clk),
        .rst  (rst),
        .UP   (tick & (state == S_REACT)),
        .DW   (1'b0),
        .LD   (state == S_IDLE),
        .Din  (5'b0),
        .Q    (react_time_Q),
        .UTC  (react_UTC),
        .DTC  ()
    );

   
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

 
    flash #(.HALF_PERIOD(FLASH_HALF)) flash_inst (
        .clk(clk), .rst(rst),
        .enable(state == S_DISPLAY),
        .flash_out(flash_out)
    );

   
    always @(posedge clk) begin
        if (rst) state <= S_IDLE;
        else     state <= next_state;
    end

   
    always @(*) begin
        next_state = state;
        case (state)
            S_IDLE:    next_state = S_WAIT;  // rst released = go!
            S_WAIT:    if (wait_done && tick)            next_state = S_REACT;
            S_REACT:   if (correct_press || react_UTC)   next_state = S_DISPLAY;
            S_DISPLAY: if (rst)                          next_state = S_IDLE;
            default:   next_state = S_IDLE;
        endcase
    end
// 7 seg 

    wire [3:0] display_digit = (react_time_Q > 5'd9) ? 4'd9 : react_time_Q[3:0];

    // Segment encoding
    wire [6:0] digit_segs;
    hex7seg seg_enc (
        .digit(display_digit),
        .segs (digit_segs)
    );

  
    localparam [6:0] SEG_DASH  = 7'b100_0000;
    localparam [6:0] SEG_BLANK = 7'b000_0000;

    reg [7:0] seg_r;   // {dp, G,F,E,D,C,B,A}

    always @(*) begin
        case (state)
            S_IDLE:    seg_r = {1'b0, SEG_DASH};                    // "–"
            S_WAIT:    seg_r = blink_state ? {1'b0, SEG_DASH}       // blinking "–"
                                           : {1'b0, SEG_BLANK};
            S_REACT:   seg_r = {1'b0, SEG_BLANK};                   // blank while reacting
            S_DISPLAY: seg_r = {1'b1, digit_segs};                  // "4." = 0.4s
            default:   seg_r = {1'b0, SEG_BLANK};
        endcase
    end

    assign seg_out = seg_r;

endmodule
