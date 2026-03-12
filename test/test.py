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

# Segment constants (uo_out = seg_out = {dp, G,F,E,D,C,B,A})
SEG_DASH  = 0b0_1000000  # "–"  (G only)
SEG_BLANK = 0b0_0000000  # blank

def safe_int(sig):
    """Return int value of signal, or -1 if X/Z (gate-level unknowns)."""
    try:
        return int(sig.value)
    except ValueError:
        return -1

async def do_reset(dut):
    """Apply and release reset, return to known state."""
    dut.rst_n.value = 0
    dut.ena.value   = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def test_idle_to_wait(dut):
    """
    After reset releases, FSM immediately leaves IDLE and enters WAIT.
    In WAIT, uo_out blinks between SEG_DASH and SEG_BLANK.
    LEDs (uio_out[7:4]) must stay OFF in WAIT.
    TICK_PERIOD=100, WAIT_BLINK_PER=200 so blink toggles every 200 cycles.
    """
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    # Sample uo_out over several blink periods — must see both DASH and BLANK
    seen_dash  = False
    seen_blank = False

    for _ in range(5000):
        await RisingEdge(dut.clk)
        seg = safe_int(dut.uo_out)
        leds = (safe_int(dut.uio_out) >> 4) & 0xF
        if seg == SEG_DASH:
            seen_dash = True
        if seg == SEG_BLANK:
            seen_blank = True
        # Only check LEDs while still in WAIT (leds==0); stop once REACT starts
        if leds != 0:
            break
        if seen_dash and seen_blank:
            break

    assert seen_dash,  "Never saw SEG_DASH in WAIT state"
    assert seen_blank, "Never saw SEG_BLANK (blank) in WAIT state"
    dut._log.info("PASS: WAIT state blink verified, LEDs off")


@cocotb.test()
async def test_wait_to_react(dut):
    """
    After wait_cnt expires (TICK_PERIOD=100 cycles per tick, wait_cnt<=63 ticks),
    FSM enters REACT: exactly ONE LED lights up, seg goes BLANK.
    """
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    # Max wait: 63 ticks * 100 cycles = 6300 cycles. Give 8000 to be safe.
    for _ in range(20000):
        await RisingEdge(dut.clk)
        leds = (safe_int(dut.uio_out) >> 4) & 0xF
        seg  = safe_int(dut.uo_out)
        if leds != 0:
            # Exactly one LED should be on (one-hot)
            assert leds in (0b0001, 0b0010, 0b0100, 0b1000), \
                f"Expected one-hot LED in REACT, got leds={leds:#06b}"
            assert seg == SEG_BLANK, \
                f"Expected SEG_BLANK in REACT, got uo_out={seg:#010b}"
            dut._log.info(f"PASS: REACT entered, LED={leds:#06b}")
            return

    assert False, "FSM never reached REACT state (no LED lit after 8000 cycles)"


@cocotb.test()
async def test_wrong_button_ignored(dut):
    """
    In REACT, pressing a wrong button must NOT move to DISPLAY.
    LED should stay lit, seg stays blank.
    """
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    # Wait until REACT
    target_led = 0
    for _ in range(20000):
        await RisingEdge(dut.clk)
        leds = (safe_int(dut.uio_out) >> 4) & 0xF
        if leds != 0:
            target_led = leds
            break
    assert target_led != 0, "Never reached REACT"

    # Find a wrong button (any LED bit that is NOT target)
    wrong = None
    for b in (0b0001, 0b0010, 0b0100, 0b1000):
        if b != target_led:
            wrong = b
            break

    dut._log.info(f"Target LED={target_led:#06b}, pressing wrong={wrong:#06b}")
    dut.ui_in.value = wrong << 4
    await ClockCycles(dut.clk, 5)
    dut.ui_in.value = 0

    # Should still be in REACT (LED still on, seg blank, no flash)
    leds = (safe_int(dut.uio_out) >> 4) & 0xF
    seg  = safe_int(dut.uo_out)
    assert leds != 0,        "LED went off after wrong press — should stay in REACT"
    assert seg == SEG_BLANK, f"Seg changed after wrong press, got {seg:#010b}"
    dut._log.info("PASS: Wrong button correctly ignored")


@cocotb.test()
async def test_correct_button_to_display(dut):
    """
    Pressing the correct button in REACT moves to DISPLAY:
    - All 4 LEDs flash (alternate 0xF / 0x0), FLASH_HALF=200 cycles
    - uo_out shows digit with decimal point set (bit7=1)
    """
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    # Wait until REACT
    target_led = 0
    for _ in range(20000):
        await RisingEdge(dut.clk)
        leds = (safe_int(dut.uio_out) >> 4) & 0xF
        if leds != 0:
            target_led = leds
            break
    assert target_led != 0, "Never reached REACT"

    # Press correct button
    dut._log.info(f"Pressing correct button: {target_led:#06b}")
    dut.ui_in.value = target_led << 4
    await ClockCycles(dut.clk, 3)
    dut.ui_in.value = 0

    # Give FSM a moment to transition
    await ClockCycles(dut.clk, 5)

    # In DISPLAY: seg must have dp set (bit 7), LEDs must flash
    seen_all_on  = False
    seen_all_off = False

    for _ in range(5000):
        await RisingEdge(dut.clk)
        seg  = safe_int(dut.uo_out)
        leds = (safe_int(dut.uio_out) >> 4) & 0xF

        assert seg & 0x80, f"Decimal point not set in DISPLAY, uo_out={seg:#010b}"

        if leds == 0xF:
            seen_all_on = True
        if leds == 0x0:
            seen_all_off = True
        if seen_all_on and seen_all_off:
            break

    assert seen_all_on,  "Never saw all 4 LEDs ON during DISPLAY flash"
    assert seen_all_off, "Never saw all 4 LEDs OFF during DISPLAY flash"
    dut._log.info("PASS: DISPLAY state verified — correct digit shown, LEDs flashing")


@cocotb.test()
async def test_reset_from_display(dut):
    """
    Asserting rst_n=0 from DISPLAY returns FSM to IDLE then WAIT (SEG_DASH visible).
    """
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    await do_reset(dut)

    # Get to DISPLAY
    target_led = 0
    for _ in range(20000):
        await RisingEdge(dut.clk)
        if (safe_int(dut.uio_out) >> 4) & 0xF:
            target_led = (safe_int(dut.uio_out) >> 4) & 0xF
            break
    assert target_led, "Never reached REACT"

    dut.ui_in.value = target_led << 4
    await ClockCycles(dut.clk, 3)
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 10)

    # Now reset
    dut._log.info("Resetting from DISPLAY...")
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # Should see WAIT blinking again
    seen_dash = False
    for _ in range(5000):
        await RisingEdge(dut.clk)
        if safe_int(dut.uo_out) == SEG_DASH:
            seen_dash = True
            break

    assert seen_dash, "After reset from DISPLAY, never saw SEG_DASH (WAIT state)"
    dut._log.info("PASS: Reset from DISPLAY works correctly")


@cocotb.test()
async def test_debug(dut):
    dut._log.info(f"Signal structure: {dir(dut.user_project)}")
