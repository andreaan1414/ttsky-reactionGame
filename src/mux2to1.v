module mux2to1 (
    input  wire        s,
    input  wire [4:0]  i0,
    input  wire [4:0]  i1,
    output wire [4:0]  y
);
    assign y = (~{5{s}} & i0) | ({5{s}} & i1);
endmodule
