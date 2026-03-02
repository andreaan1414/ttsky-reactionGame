module countUD5L (
    input  wire       clkin,
    input  wire       rst,
    input  wire       UP,
    input  wire       DW,
    input  wire       LD,
    input  wire [4:0] Din,
    output wire [4:0] Q,
    output wire       UTC,
    output wire       DTC
);
    wire [4:0] addsub_result;
    wire [4:0] mux_out;
    wire       ovfl;
    wire       enable_count;

    assign UTC          = &Q;          // all 1s = 5'b11111
    assign DTC          = ~|Q;         // all 0s = 5'b00000
    assign enable_count = (UP ^ DW) | LD;

    // +1 when UP, -1 when DW
    AddSub5 my_addOrSub (
        .A  (Q),
        .B  (5'b1),
        .sub(DW & ~UP),
        .S  (addsub_result),
        .ovfl(ovfl)
    );

    // Select: load Din or increment/decrement result
    mux2to1 my_mux (
        .s  (LD),
        .i0 (addsub_result),
        .i1 (Din),
        .y  (mux_out)
    );

    // Registered output
    reg [4:0] q_r;
    assign Q = q_r;

    always @(posedge clkin) begin
        if (rst)
            q_r <= 5'b0;
        else if (enable_count)
            q_r <= mux_out;
    end
endmodule
