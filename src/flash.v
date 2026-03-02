module flash #(
    parameter HALF_PERIOD = 12_500_000
) (
    input  wire clk,
    input  wire rst,
    input  wire enable,
    output reg  flash_out
);
    reg [24:0] cnt;

    always @(posedge clk) begin
        if (rst || !enable) begin
            cnt <= 25'd0;
            flash_out <= 1'b0;
        end else if (cnt == HALF_PERIOD - 1) begin
            cnt  <= 25'd0;
            flash_out <= ~flash_out;
        end else begin
            cnt <= cnt + 1'b1;
        end
    end
endmodule
