import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# Constants and Helpers (Keep these as they were)
BTN4, BTN5, BTN6, BTN7 = 0x10, 0x20, 0x40, 0x80
BTNS = [BTN4, BTN5, BTN6, BTN7]
SEG_DASH, SEG_DP, FLASH_HALF = 0x40, 0x80, 200
TICK, MAX_WAIT = 100, 6400

async def do_reset(dut):
    dut.ena.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)

async def release_reset(dut):
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

async def press_button(dut, btn_mask):
    dut.ui_in.value = btn_mask
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 1)

async def wait_for_react_state(dut):
    for _ in range(MAX_WAIT + 500):
        await RisingEdge(dut.clk)
        leds = int(dut.uio_out.value) & 0xF0
        if leds != 0: return leds
    raise AssertionError("Timeout")

# 

@cocotb.test()
async def test_suite(dut):
    # DEBUG: Uncomment this line if it still fails to see the real path
    # dut._log.info(f"DEBUG: Children: {list(dut._sub_handles.keys())}")
    
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    # Helper to access the FSM instance dynamically
    # It tries 'game', then 'user_project.game'
    if hasattr(dut, 'game'):
        fsm = dut.game
    elif hasattr(dut, 'user_project') and hasattr(dut.user_project, 'game'):
        fsm = dut.user_project.game
    else:
        fsm = dut # Fallback

    # --- Test 01/02 ---
    await do_reset(dut)
    await release_reset(dut)
    assert int(fsm.state.value) == 1

    # --- Test 03: LFSR ---
    samples = set()
    for _ in range(20):
        await RisingEdge(dut.clk)
        val = int(fsm.lfsr_inst.rnd.value)
        samples.add(val)
    assert len(samples) > 1

    # --- Test 04/05/06: Logic ---
    lit = await wait_for_react_state(dut)
    await press_button(dut, lit)
    await ClockCycles(dut.clk, 3)
    assert int(fsm.state.value) == 3 # Should be DISPLAY

    # --- Test 07: Display ---
    # Accessing flash_inst via the FSM object found earlier
    for _ in range(FLASH_HALF * 3):
        await RisingEdge(dut.clk)
        if int(fsm.flash_inst.flash_out.value) == 0:
            break
    seg = int(dut.uo_out.value)
    assert (seg & SEG_DP) != 0 # Decimal point check

    # --- Test 08: Flash ---
    snap1 = int(dut.uio_out.value) & 0xF0
    await ClockCycles(dut.clk, FLASH_HALF * 2 + 20)
    snap2 = int(dut.uio_out.value) & 0xF0
    assert snap1 != snap2, "LEDs did not flash"

    dut._log.info("All tests passed with dynamic pathing!")
