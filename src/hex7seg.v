module hex7seg (
    input  wire [3:0] digit,
    output reg  [6:0] segs    // {G,F,E,D,C,B,A}
);
    always @(*) begin
        case (digit)
            4'd0: segs = 7'b011_1111;
            4'd1: segs = 7'b000_0110;
            4'd2: segs = 7'b101_1011;
            4'd3: segs = 7'b100_1111;
            4'd4: segs = 7'b110_0110;
            4'd5: segs = 7'b110_1101;
            4'd6: segs = 7'b111_1101;
            4'd7: segs = 7'b000_0111;
            4'd8: segs = 7'b111_1111;
            4'd9: segs = 7'b110_1111;
            default: segs = 7'b000_0000; // blank
        endcase
    end
endmodule
