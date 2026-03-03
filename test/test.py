import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# Constants
BTN4, BTN5, BTN6, BTN7 = 0x10, 0x20, 0x40, 0x80
BTNS = [BTN4, BTN5, BTN6, BTN7]
SEG_DASH, SEG_DP, FLASH_HALF = 0x40, 0x80, 200
TICK, MAX_WAIT = 100, 6400

# Helper to find the FSM instance dynamically
def get_fsm(dut):
    # This searches the hierarchy for the instance named 'game'
    if hasattr(dut, 'game'): return dut.game
    if hasattr(dut, 'user_project'):
        if hasattr(dut.user_project, 'game'): return dut.user_project.game
    if hasattr(dut, 'uut'):
        if hasattr(dut.uut, 'game'): return dut.uut.game
    return dut # Fallback if direct access

async def do_reset(dut):
    dut.ena.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)

async def release_reset(dut):
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

async def wait_for_react_state(dut):
    for _ in range(MAX_WAIT + 500):
        await RisingEdge(dut.clk)
        leds = int(dut.uio_out.value) & 0xF0
        if leds != 0: return leds
    raise AssertionError("Timeout")



@cocotb.test()
async def test_suite(dut):
    fsm = get_fsm(dut)
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    # --- Test 01 & 02 ---
    await do_reset(dut)
    await release_reset(dut)
    assert int(fsm.state.value) == 1, "Should be in WAIT state"

    # --- Test 03: LFSR ---
    samples = {int(fsm.lfsr_inst.rnd.value) for _ in range(20)}
    assert len(samples) > 1, "LFSR not advancing"

    # --- Test 04, 05, 06: Gameplay ---
    lit = await wait_for_react_state(dut)
    dut.ui_in.value = lit # Press button
    await ClockCycles(dut.clk, 5)
    assert int(fsm.state.value) == 3, "Should be in DISPLAY"

    # --- Test 07: Display ---
    for _ in range(FLASH_HALF * 3):
        await RisingEdge(dut.clk)
        if int(fsm.flash_inst.flash_out.value) == 0: break
    assert (int(dut.uo_out.value) & 0x80) != 0, "Decimal point missing"

    # --- Test 08: Flash ---
    snap1 = int(dut.uio_out.value) & 0xF0
    await ClockCycles(dut.clk, FLASH_HALF * 2 + 20)
    assert snap1 != (int(dut.uio_out.value) & 0xF0), "LEDs failed to flash"

    # --- Test 09: Overflow ---
    await do_reset(dut)
    await release_reset(dut)
    await ClockCycles(dut.clk, 33 * TICK)
    assert int(fsm.state.value) == 3
    assert int(fsm.react_counter.Q.value) == 31, "Counter overflow failure"

    dut._log.info("All hierarchy-corrected tests passed!")
