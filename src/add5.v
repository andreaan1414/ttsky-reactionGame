module add5 (
    input  wire [4:0] A,
    input  wire [4:0] B,
    input  wire       Cin,
    output wire [4:0] S,
    output wire       ovfl,
    output wire       Cout
);
    wire [4:0] Carry;

    FA my1 (.a(A[0]), .b(B[0]), .C_i(Cin),      .FA_sum(S[0]), .C_o(Carry[0]));
    FA my2 (.a(A[1]), .b(B[1]), .C_i(Carry[0]), .FA_sum(S[1]), .C_o(Carry[1]));
    FA my3 (.a(A[2]), .b(B[2]), .C_i(Carry[1]), .FA_sum(S[2]), .C_o(Carry[2]));
    FA my4 (.a(A[3]), .b(B[3]), .C_i(Carry[2]), .FA_sum(S[3]), .C_o(Carry[3]));
    FA my5 (.a(A[4]), .b(B[4]), .C_i(Carry[3]), .FA_sum(S[4]), .C_o(Carry[4]));

    assign ovfl = Carry[4] ^ Carry[3];
    assign Cout = Carry[4];
endmodule


module AddSub5 (
    input  wire [4:0] A,
    input  wire [4:0] B,
    input  wire       sub,     // 1 = subtract, 0 = add
    output wire [4:0] S,
    output wire       ovfl
);
    wire       cout;
    wire [4:0] b_sub = B ^ {5{sub}};   // invert B when subtracting

    add5 subi0 (
        .A(A), .B(b_sub), .Cin(sub),
        .S(S), .Cout(cout), .ovfl(ovfl)
    );
endmodule
