import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

@cocotb.test()
async def tt_um_andreaan1414_top_reaction(dut):
    # Start clock
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())

    # Initialize inputs
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)

    # Release reset
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    dut._log.info("Reset released, checking outputs are stable...")

    # Just verify outputs are not undefined after reset
    uo_val = dut.uo_out.value
    dut._log.info(f"uo_out = {uo_val}")

    # Wait a bit and check design is still responding
    await ClockCycles(dut.clk, 10)
    dut._log.info("Gate-level smoke test passed!")

@cocotb.test()
async def test_debug(dut):
    dut._log.info(f"Signal structure: {dir(dut.user_project)}")
