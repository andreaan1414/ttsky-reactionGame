import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# Constants
BTN4, BTN5, BTN6, BTN7 = 0x10, 0x20, 0x40, 0x80
SEG_DASH, SEG_DP, FLASH_HALF = 0x40, 0x80, 200
TICK = 100

async def do_reset(dut):
    dut.ena.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)

async def release_reset(dut):
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)



@cocotb.test()
async def test_reaction_game(dut):
    # 'uut' is the instance in tb.v, 'game' is the instance in top_reaction.v
    fsm = dut.uut.game 
    
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    # --- Test 01: Reset/IDLE ---
    await do_reset(dut)
    assert int(dut.uo_out.value) == SEG_DASH, "7-seg should show dash in IDLE"
    
    # --- Test 02: WAIT ---
    await release_reset(dut)
    assert int(fsm.state.value) == 1, "Should be in WAIT (1)"

    # --- Test 03: LFSR ---
    # Path: dut -> uut -> game -> lfsr_inst -> rnd
    samples = {int(fsm.lfsr_inst.rnd.value) for _ in range(10)}
    assert len(samples) > 1, "LFSR not advancing"

    # --- Test 07: Display/Time ---
    # Trigger reaction
    await ClockCycles(dut.clk, 3 * TICK)
    # Simulate button press (ui_in is at top level)
    dut.ui_in.value = 0x80 
    await ClockCycles(dut.clk, 2)
    dut.ui_in.value = 0
    
    # Path: dut -> uut -> game -> flash_inst -> flash_out
    for _ in range(FLASH_HALF * 3):
        await RisingEdge(dut.clk)
        if int(fsm.flash_inst.flash_out.value) == 0: break
        
    assert (int(dut.uo_out.value) & SEG_DP) != 0, "Decimal point missing in DISPLAY"
    dut._log.info("Tests passed!")



@cocotb.test()
async def test_debug(dut):
    # This will print all signals in the hierarchy to your console
    dut._log.info(f"Signal structure: {dir(dut.user_project)}")
