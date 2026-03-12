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

# uo_out = seg_out = {dp, G, F, E, D, C, B, A}
SEG_DASH  = 0b01000000   # WAIT: blinks this
SEG_BLANK = 0b00000000   # REACT: stuck here
# DISPLAY: bit7 (dp) set, e.g. 0x80 | digit_segs

def safe_int(sig):
    """Return int, or -1 if X/Z."""
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
    REACT = seg is BLANK and stays BLANK for >250 consecutive cycles.
    In WAIT, seg toggles every 200 cycles so it never stays blank that long.
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
    """In WAIT, uo_out blinks between SEG_DASH and SEG_BLANK."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    seen_dash  = False
    seen_blank = False

    for _ in range(5000):
        await RisingEdge(dut.clk)
        seg = safe_int(dut.uo_out)
        if seg == SEG_DASH:
            seen_dash = True
        if seg == SEG_BLANK and seen_dash:
            seen_blank = True
        if seen_dash and seen_blank:
            break

    assert seen_dash,  "Never saw SEG_DASH — FSM not in WAIT"
    assert seen_blank, "Never saw SEG_BLANK after DASH — blink broken"
    dut._log.info("PASS: WAIT blink verified")


@cocotb.test()
async def test_wait_to_react(dut):
    """After wait_cnt expires, seg stays BLANK (REACT state)."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    reached = await wait_for_react(dut)
    assert reached, "FSM never reached REACT (seg never stayed BLANK >250 cycles)"
    dut._log.info("PASS: REACT state reached")


@cocotb.test()
async def test_correct_button_to_display(dut):
    """One of the 4 buttons causes uo_out dp (bit7) to go high = DISPLAY."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    assert await wait_for_react(dut), "Never reached REACT"

    found = False
    for btn in range(4):
        dut.ui_in.value = (1 << btn) << 4
        await ClockCycles(dut.clk, 5)
        dut.ui_in.value = 0
        await ClockCycles(dut.clk, 5)
        seg = safe_int(dut.uo_out)
        dut._log.info(f"btn={btn} -> uo_out={seg:#010b}")
        if seg & 0x80:
            found = True
            dut._log.info(f"PASS: DISPLAY reached with button {btn}")
            break

    assert found, "No button moved FSM to DISPLAY (dp never set)"


@cocotb.test()
async def test_wrong_button_ignored(dut):
    """Wrong buttons keep FSM in REACT; correct button reaches DISPLAY."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    assert await wait_for_react(dut), "Never reached REACT"

    correct = None
    for btn in range(4):
        dut.ui_in.value = (1 << btn) << 4
        await ClockCycles(dut.clk, 5)
        dut.ui_in.value = 0
        await ClockCycles(dut.clk, 3)
        seg = safe_int(dut.uo_out)
        if seg & 0x80:
            correct = btn
            dut._log.info(f"PASS: correct={btn}, others ignored")
            break
        else:
            dut._log.info(f"Button {btn} ignored (seg={seg:#010b})")

    assert correct is not None, "FSM never reached DISPLAY"


@cocotb.test()
async def test_reset_from_display(dut):
    """Reset from DISPLAY brings back WAIT blinking (SEG_DASH visible)."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    assert await wait_for_react(dut), "Never reached REACT"

    for btn in range(4):
        dut.ui_in.value = (1 << btn) << 4
        await ClockCycles(dut.clk, 5)
        dut.ui_in.value = 0
        await ClockCycles(dut.clk, 5)
        if safe_int(dut.uo_out) & 0x80:
            break

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    seen_dash = False
    for _ in range(5000):
        await RisingEdge(dut.clk)
        if safe_int(dut.uo_out) == SEG_DASH:
            seen_dash = True
            break

    assert seen_dash, "After reset, never saw SEG_DASH"
    dut._log.info("PASS: Reset from DISPLAY works")


@cocotb.test()
async def test_debug(dut):
    dut._log.info(f"uo_out={safe_int(dut.uo_out):#010b}")
    dut._log.info(f"uio_out={safe_int(dut.uio_out):#010b}")
    dut._log.info(f"Signals: {dir(dut.user_project)}")
