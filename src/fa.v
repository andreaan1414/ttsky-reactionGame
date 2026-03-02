module FA (
    input  wire a,
    input  wire b,
    input  wire C_i,
    output wire FA_sum,
    output wire C_o
);
    assign C_o    = (a & b) | (C_i & (a ^ b));
    assign FA_sum = (a ^ b) ^ C_i;
endmodule
