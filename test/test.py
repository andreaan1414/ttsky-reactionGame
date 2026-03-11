import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer
import os

GATES = os.environ.get('GATES', 'no') == 'yes'

@cocotb.test()
async def tt_um_andreaan1414_top_reaction(dut):
    # Start clock (40ns = 25MHz)
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    # inputs 
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)

    #  reset
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    dut._log.info("Reset released")

    # wait some cycles  reset
    uo_val = int(dut.uo_out.value)
    dut._log.info(f"uo_out after reset: {uo_val:#010b}")

    # wait
    dut._log.info("Waiting for REACT state (letting timer expire)...")
    await ClockCycles(dut.clk, 300)  # Give plenty of cycles for timer to expire


    dut._log.info("Trying button presses to find correct target...")
    found = False
    for btn in range(1, 5):  # buttons are bits in ui_in[7:4]
        dut.ui_in.value = btn << 4
        await ClockCycles(dut.clk, 3)
        dut.ui_in.value = 0
        uo_val = int(dut.uo_out.value)
        dut._log.info(f"  Pressed btn {btn}, uo_out={uo_val:#010b}")
        if uo_val != 0:  # DISPLAY state should show something on 7seg
            found = True
            dut._log.info(f"  -> Got non-zero output with btn {btn}, likely in DISPLAY!")
            break
        await ClockCycles(dut.clk, 5)

    assert found, "No button press produced a non-zero output — FSM may not be reaching DISPLAY"
    dut._log.info("PASS: FSM reached DISPLAY state")


@cocotb.test()
async def test_debug(dut):
    dut._log.info(f"Signal structure: {dir(dut.user_project)}")
