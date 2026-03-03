import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# Constants
S_IDLE, S_WAIT, S_REACT, S_DISPLAY = 0, 1, 2, 3

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
    assert int(fsm.state.value) == S_WAIT, f"Expected WAIT(1) after release, got {fsm.state.value}"
    dut._log.info("WAIT state verified")
    
    # --- Test 03: WAIT -> REACT (Force Bypass) ---
    dut._log.info("Forcing wait_cnt to 0 to bypass LFSR delay...")
    fsm.wait_cnt.value = 0  # Manually force the timer to zero to speed up testing
    await ClockCycles(dut.clk, 2)
    
    assert int(fsm.state.value) == S_REACT, f"Failed to reach REACT, currently {fsm.state.value}"
    dut._log.info("REACT state verified via timer bypass")

    # --- Test 04: REACT -> DISPLAY (Correct Press) ---
    # Drive correct button: target_led is calculated in reaction_fsm.v
    # We must read what the target is to simulate a correct press
    target = int(fsm.target_led.value)
    dut.ui_in.value = target << 4  # Shift into ui_in[7:4]
    await ClockCycles(dut.clk, 2)
    
    assert int(fsm.state.value) == S_DISPLAY, "Failed to reach DISPLAY after correct press"
    dut._log.info("DISPLAY state verified")

@cocotb.test()
async def test_debug(dut):
    # This will print all signals in the hierarchy to your console
    dut._log.info(f"Signal structure: {dir(dut.user_project)}")
