/*
 * Copyright (c) 2024 Andrea Arreortua
 * SPDX-License-Identifier: Apache-2.0
 *
 * tt_um_andreaan1414_top_reaction
 *
 */
`default_nettype none

module tt_um_andreaan1414_top_reaction (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    // rst_n is active-low on TT; our FSM uses active-high rst
    wire rst = ~rst_n;

    // Bidir pin directions: top 4 = outputs (LEDs), bottom 4 = unused inputs
    assign uio_oe = 8'b1111_0000;

    // Bottom 4 bidir outputs unused
    assign uio_out[3:0] = 4'b0000;

    // Game core
    wire [3:0] led_out;
    wire [7:0] seg_out;

    reaction_fsm game (
        .clk    (clk),
        .rst    (rst),
        .btn_in (ui_in[7:4]),    
        .led_out(led_out),     
        .seg_out(seg_out)        
    );

    // Wire LEDs to upper bidir outputs
    assign uio_out[7:4] = led_out;

    // Wire 7-seg to dedicated outputs
    assign uo_out = seg_out;

    // Suppress unused input warnings
    wire _unused = &{ena, uio_in, ui_in[3:0], 1'b0};

endmodule

