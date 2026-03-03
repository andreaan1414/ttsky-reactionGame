import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

@cocotb.test()
async def test_reaction_game(dut):
    # 1. Initialize inputs to a stable state BEFORE starting the clock
    dut.rst_n.value = 1  # Deassert reset first
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    
    # 2. Start clock
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    # 3. Perform Reset Sequence
    dut._log.info("Resetting...")
    dut.rst_n.value = 0  # Active reset
    dut.ena.value = 1    # Enable the module
    await ClockCycles(dut.clk, 5)
    
    # 4. Check that we are in IDLE (state 0) while reset is held
    fsm = dut.user_project.game
    assert int(fsm.state.value) == 0, f"Expected IDLE(0) during reset, got {fsm.state.value}"
    
    # 5. Release Reset
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    
    dut._log.info("Reset released, starting tests...")

    # --- Test 02: WAIT ---
    # After releasing reset, it should transition to S_WAIT (1)
    await ClockCycles(dut.clk, 2)
    assert int(fsm.state.value) == 1, f"Expected WAIT(1) after release, got {fsm.state.value}"
    dut._log.info("WAIT state verified")
    
    # ... rest of your tests ...
