module lfsr (
    input  wire       clk,
    input  wire       rst,
    output reg  [7:0] rnd,
    output wire [5:0] Q
);
    wire xor_fb = rnd[0] ^ rnd[5] ^ rnd[6] ^ rnd[7];

    always @(posedge clk) begin
        if (rst)
            rnd <= 8'b1000_0001;
        else
            rnd <= {rnd[6:0], xor_fb};
    end

    assign Q = rnd[7:2];   // 6-bit random output
endmodule
