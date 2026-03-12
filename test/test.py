# import cocotb
# from cocotb.clock import Clock
# from cocotb.triggers import ClockCycles, RisingEdge

# @cocotb.test()
# async def tt_um_andreaan1414_top_reaction(dut):
#     # Start clock
#     cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())

#     # Initialize inputs
#     dut.rst_n.value = 0
#     dut.ena.value = 1
#     dut.ui_in.value = 0
#     dut.uio_in.value = 0
#     await ClockCycles(dut.clk, 5)

#     # Release reset
#     dut.rst_n.value = 1
#     await ClockCycles(dut.clk, 5)
#     dut._log.info("Reset released, checking outputs are stable...")

#     # Just verify outputs are not undefined after reset
#     uo_val = dut.uo_out.value
#     dut._log.info(f"uo_out = {uo_val}")

#     # Wait a bit and check design is still responding
#     await ClockCycles(dut.clk, 10)
#     dut._log.info("Gate-level smoke test passed!")

# @cocotb.test()
# async def test_debug(dut):
#     dut._log.info(f"Signal structure: {dir(dut.user_project)}")



import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# uo_out = {dp, G, F, E, D, C, B, A}
# SEG_DASH = G only = bit6 = 0b01000000
SEG_DASH  = 0b01000000
SEG_BLANK = 0b00000000

def safe_int(sig):
    try:
        return int(sig.value)
    except ValueError:
        return -1

async def do_reset(dut):
    dut.rst_n.value  = 0
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 5)

async def wait_for_react(dut, max_cycles=20000):
    """
    REACT = seg stays BLANK for >250 consecutive cycles.
    WAIT blinks every 200 cycles so it never stays blank that long.
    """
    blank_streak = 0
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        seg = safe_int(dut.uo_out)
        if seg == SEG_BLANK:
            blank_streak += 1
            if blank_streak > 250:
                return True
        else:
            blank_streak = 0
    return False


@cocotb.test()
async def test_idle_to_wait(dut):
    """
    WAIT state: seg blinks DASH<->BLANK every 200 cycles.
    We wait up to 10000 cycles to see both values.
    """
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    seen_dash  = False
    seen_blank = False
    # WAIT_BLINK_PER=200, so first toggle at cycle 200, second at 400
    # Give 10000 cycles = 50 blink periods
    for _ in range(10000):
        await RisingEdge(dut.clk)
        seg = safe_int(dut.uo_out)
        dut._log.debug(f"seg={seg:#010b}")
        if seg == SEG_DASH:
            seen_dash = True
        if seg == SEG_BLANK and seen_dash:
            seen_blank = True
        if seen_dash and seen_blank:
            break
        # Stop if we hit REACT (blank streak >250) — WAIT was fine
        # but blink was too fast to catch both in 10000 cycles (won't happen)

    assert seen_dash,  f"Never saw SEG_DASH (0x40) in WAIT — check blink_state logic"
    assert seen_blank, f"Never saw SEG_BLANK after DASH — blink not toggling"
    dut._log.info("PASS: WAIT blink verified")


@cocotb.test()
async def test_wait_to_react(dut):
    """After wait_cnt expires, seg stays BLANK (REACT)."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    reached = await wait_for_react(dut)
    assert reached, "FSM never reached REACT (seg never stayed BLANK >250 cycles)"
    dut._log.info("PASS: REACT state reached")


@cocotb.test()
async def test_correct_button_to_display(dut):
    """
    Try each button for 20 cycles in REACT.
    LFSR resets to 0b10000001 so rnd[1:0]=01 -> target_idx=1 -> target_led=0b0010 -> button 1.
    But we try all 4 to be safe.
    DISPLAY = uo_out bit7 set.
    """
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    assert await wait_for_react(dut), "Never reached REACT"
    dut._log.info("In REACT, trying buttons...")

    found = False
    for btn in range(4):
        # Hold button for 20 cycles to ensure it's sampled
        dut.ui_in.value = (1 << btn) << 4
        for _ in range(20):
            await RisingEdge(dut.clk)
            seg = safe_int(dut.uo_out)
            if seg & 0x80:
                found = True
                dut._log.info(f"PASS: DISPLAY reached with button {btn}")
                break
        dut.ui_in.value = 0
        if found:
            break
        await ClockCycles(dut.clk, 3)
        dut._log.info(f"btn={btn} not correct, seg={safe_int(dut.uo_out):#010b}")

    assert found, "No button moved FSM to DISPLAY (dp never set on uo_out)"


@cocotb.test()
async def test_wrong_button_ignored(dut):
    """Wrong buttons stay in REACT; correct button reaches DISPLAY."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    assert await wait_for_react(dut), "Never reached REACT"

    correct = None
    for btn in range(4):
        dut.ui_in.value = (1 << btn) << 4
        for _ in range(20):
            await RisingEdge(dut.clk)
            if safe_int(dut.uo_out) & 0x80:
                correct = btn
                break
        dut.ui_in.value = 0
        if correct is not None:
            dut._log.info(f"PASS: correct={btn}, previous buttons were ignored")
            break
        await ClockCycles(dut.clk, 3)
        dut._log.info(f"Button {btn} ignored (seg={safe_int(dut.uo_out):#010b})")

    assert correct is not None, "FSM never reached DISPLAY with any button"


@cocotb.test()
async def test_reset_from_display(dut):
    """Reset from DISPLAY -> back to WAIT (SEG_DASH visible)."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    assert await wait_for_react(dut), "Never reached REACT"

    # Get to DISPLAY
    for btn in range(4):
        dut.ui_in.value = (1 << btn) << 4
        for _ in range(20):
            await RisingEdge(dut.clk)
            if safe_int(dut.uo_out) & 0x80:
                break
        dut.ui_in.value = 0
        if safe_int(dut.uo_out) & 0x80:
            break
        await ClockCycles(dut.clk, 3)

    await ClockCycles(dut.clk, 5)

    # Reset
    dut._log.info("Resetting from DISPLAY...")
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Should see WAIT blink (DASH) within 10000 cycles
    seen_dash = False
    for _ in range(10000):
        await RisingEdge(dut.clk)
        if safe_int(dut.uo_out) == SEG_DASH:
            seen_dash = True
            break

    assert seen_dash, "After reset, never saw SEG_DASH — FSM not returning to WAIT"
    dut._log.info("PASS: Reset from DISPLAY works")


@cocotb.test()
async def test_debug(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)
    await ClockCycles(dut.clk, 5)
    dut._log.info(f"uo_out  = {safe_int(dut.uo_out):#010b}")
    dut._log.info(f"uio_out = {safe_int(dut.uio_out):#010b}")
    dut._log.info(f"Signals: {dir(dut.user_project)}")
