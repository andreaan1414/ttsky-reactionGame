# # SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# # SPDX-License-Identifier: Apache-2.0

# import cocotb
# from cocotb.clock import Clock
# from cocotb.triggers import ClockCycles


# @cocotb.test()
# async def test_project(dut):
#     dut._log.info("Start")

#     # Set the clock period to 10 us (100 KHz)
#     clock = Clock(dut.clk, 10, unit="us")
#     cocotb.start_soon(clock.start())

#     # Reset
#     dut._log.info("Reset")
#     dut.ena.value = 1
#     dut.ui_in.value = 0
#     dut.uio_in.value = 0
#     dut.rst_n.value = 0
#     await ClockCycles(dut.clk, 10)
#     dut.rst_n.value = 1

#     dut._log.info("Test project behavior")

#     # Set the input values you want to test
#     dut.ui_in.value = 20
#     dut.uio_in.value = 30

#     # Wait for one clock cycle to see the output values
#     await ClockCycles(dut.clk, 1)

#     # The following assersion is just an example of how to check the output values.
#     # Change it to match the actual expected output of your module:
#     assert dut.uo_out.value == 50

#     # Keep testing the module by changing the input values, waiting for
#     # one or more clock cycles, and asserting the expected output values.


# stuff above is from the sample 

# SPDX-FileCopyrightText: © 2024 Your Name
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# ---------------------------------------------------------------
# Pin constants (matching pinout)
# ---------------------------------------------------------------
# ui_in[7:4] = buttons 7,6,5,4
BTN4 = 0x10   # ui_in[4]
BTN5 = 0x20   # ui_in[5]
BTN6 = 0x40   # ui_in[6]
BTN7 = 0x80   # ui_in[7]
BTNS = [BTN4, BTN5, BTN6, BTN7]

# uio_out[7:4] = LEDs 7,6,5,4
LED4 = 0x10   # uio_out[4]
LED5 = 0x20   # uio_out[5]
LED6 = 0x40   # uio_out[6]
LED7 = 0x80   # uio_out[7]
LEDS = [LED4, LED5, LED6, LED7]

# 7-seg segment patterns (uo_out[6:0] = {G,F,E,D,C,B,A})
# These must match seg7_encoder.v
SEG_DASH  = 0x40   # segment G only  = "–"
SEG_BLANK = 0x00
SEG_DP    = 0x80   # decimal point bit

# Sim timing (matches Makefile -D flags)
TICK       = 100
FLASH_HALF = 200
MAX_WAIT   = 6400  # 64 ticks × 100 cycles, safe upper bound


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def do_reset(dut):
    """Assert rst_n=0 for several cycles (hold in IDLE), then release."""
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 5)


async def release_reset(dut):
    """Release rst_n → triggers IDLE→WAIT transition (go!)."""
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


async def press_button(dut, btn_mask):
    """Pulse a reaction button for one clock cycle."""
    dut.ui_in.value = btn_mask
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 1)


async def wait_for_react_state(dut):
    """Wait until one of the 4 target LEDs lights up (REACT state)."""
    for _ in range(MAX_WAIT + 500):
        await RisingEdge(dut.clk)
        leds = int(dut.uio_out.value) & 0xF0   # upper 4 bits
        if leds != 0:
            return leds   # return which LED is lit
    raise AssertionError("Timeout waiting for a target LED to light up")


def get_lit_led(dut):
    """Return the uio_out mask of whichever LED is currently lit."""
    return int(dut.uio_out.value) & 0xF0


def led_to_btn(led_mask):
    """Convert a LED mask (uio_out[7:4]) to the matching button mask (ui_in[7:4])."""
    # LED4(0x10)→BTN4(0x10), LED5(0x20)→BTN5(0x20), etc. — same bit positions!
    return led_mask


# ---------------------------------------------------------------
# TEST 1 — Reset: 7-seg shows dash, LEDs off
# ---------------------------------------------------------------
@cocotb.test()
async def test_01_reset_idle(dut):
    """In IDLE (rst_n=0): 7-seg should show dash (SEG_G only), LEDs off."""
    dut._log.info("Test 01: reset → IDLE display")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await ClockCycles(dut.clk, 5)

    seg = int(dut.uo_out.value)
    leds = int(dut.uio_out.value) & 0xF0

    assert seg == SEG_DASH, \
        f"Expected dash (0x{SEG_DASH:02X}) in IDLE, got 0x{seg:02X}"
    assert leds == 0x00, \
        f"Expected LEDs off in IDLE, got uio_out=0x{int(dut.uio_out.value):02X}"
    dut._log.info("PASS: IDLE shows dash on 7-seg, LEDs off")


# ---------------------------------------------------------------
# TEST 2 — rst_n release → WAIT (7-seg blinks dash)
# ---------------------------------------------------------------
@cocotb.test()
async def test_02_release_goes_to_wait(dut):
    """Releasing rst_n should transition to WAIT state."""
    dut._log.info("Test 02: rst_n release → WAIT")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await release_reset(dut)

    state = int(dut.user_project.game.state.value)
    assert state == 1, f"Expected WAIT (1), got state={state}"
    dut._log.info("PASS: entered WAIT after rst_n release")


# ---------------------------------------------------------------
# TEST 3 — LFSR non-zero and advancing
# ---------------------------------------------------------------
@cocotb.test()
async def test_03_lfsr(dut):
    """LFSR must be non-zero and produce multiple distinct values."""
    dut._log.info("Test 03: LFSR non-zero and advancing")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)

    samples = set()
    for _ in range(20):
        await RisingEdge(dut.clk)
        val = int(dut.user_project.fsm.lfsr_inst.rnd.value)
        assert val != 0, "LFSR is stuck at zero!"
        samples.add(val)

    assert len(samples) > 1, f"LFSR not advancing, only {len(samples)} unique value(s)"
    dut._log.info(f"PASS: {len(samples)} distinct LFSR values in 20 cycles")


# ---------------------------------------------------------------
# TEST 4 — WAIT → REACT: one LED lights, others stay off
# ---------------------------------------------------------------
@cocotb.test()
async def test_04_wait_to_react_one_led(dut):
    """After random delay exactly one target LED must light up."""
    dut._log.info("Test 04: WAIT → REACT, single LED lights")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)

    # Exactly one of the 4 LEDs should be on (power of 2 check)
    assert lit != 0,              "No LED lit in REACT state"
    assert (lit & (lit - 1)) == 0, \
        f"More than one LED lit: uio_out[7:4]=0x{lit:02X}"

    state = int(dut.user_project.game.state.value)
    assert state == 2, f"Expected REACT (2), got state={state}"
    dut._log.info(f"PASS: single LED lit = 0x{lit:02X} in REACT state")


# ---------------------------------------------------------------
# TEST 5 — Wrong button ignored, correct button advances
# ---------------------------------------------------------------
@cocotb.test()
async def test_05_wrong_button_ignored(dut):
    """Pressing wrong button must NOT leave REACT state."""
    dut._log.info("Test 05: wrong button ignored")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)

    # Find a button that does NOT match the lit LED
    wrong_btn = None
    for btn in BTNS:
        if btn != led_to_btn(lit):
            wrong_btn = btn
            break

    assert wrong_btn is not None, "Could not find a wrong button (only 1 LED option?)"

    await press_button(dut, wrong_btn)
    await ClockCycles(dut.clk, 3)

    state = int(dut.user_project.game.state.value)
    assert state == 2, \
        f"Wrong button caused state change! Expected REACT (2), got {state}"
    dut._log.info(f"PASS: wrong button 0x{wrong_btn:02X} ignored, still in REACT")


# ---------------------------------------------------------------
# TEST 6 — Correct button → DISPLAY
# ---------------------------------------------------------------
@cocotb.test()
async def test_06_correct_button_display(dut):
    """Pressing matching button must transition to DISPLAY."""
    dut._log.info("Test 06: correct button → DISPLAY")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)

    correct_btn = led_to_btn(lit)
    await ClockCycles(dut.clk, 2 * TICK + 5)   # wait 2 ticks then react
    await press_button(dut, correct_btn)
    await ClockCycles(dut.clk, 3)

    state = int(dut.user_project.game.state.value)
    assert state == 3, \
        f"Expected DISPLAY (3) after correct button, got state={state}"
    dut._log.info(f"PASS: correct button 0x{correct_btn:02X} → DISPLAY")


# ---------------------------------------------------------------
# TEST 7 — DISPLAY shows reaction time on 7-seg with decimal point
# ---------------------------------------------------------------
@cocotb.test()
async def test_07_display_shows_time(dut):
    """7-seg in DISPLAY must show correct digit and decimal point."""
    dut._log.info("Test 07: DISPLAY shows reaction time on 7-seg")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)

    expected_ticks = 3   # react after exactly 3 ticks = 0.3s → digit "3"
    await ClockCycles(dut.clk, expected_ticks * TICK + 2)
    await press_button(dut, led_to_btn(lit))
    await ClockCycles(dut.clk, 5)

    # Wait for flash_out=0 so segments are unmasked
    for _ in range(FLASH_HALF * 3):
        await RisingEdge(dut.clk)
        if int(dut.user_project.fsm.flash_inst.flash_out.value) == 0:
            break

    seg = int(dut.uo_out.value)
    dp_on   = (seg & SEG_DP) != 0
    seg_val =  seg & 0x7F    # strip dp

    # Get expected segment pattern from a simple lookup
    seg_patterns = {
        0: 0x3F, 1: 0x06, 2: 0x5B, 3: 0x4F,
        4: 0x66, 5: 0x6D, 6: 0x7D, 7: 0x07,
        8: 0x7F, 9: 0x6F
    }
    expected_seg = seg_patterns[expected_ticks]

    assert dp_on, f"Decimal point not on in DISPLAY (uo_out=0x{seg:02X})"
    assert seg_val == expected_seg, \
        f"Expected digit {expected_ticks} (0x{expected_seg:02X}), " \
        f"got seg=0x{seg_val:02X} (uo_out=0x{seg:02X})"
    dut._log.info(
        f"PASS: 7-seg shows '{expected_ticks}.' = {expected_ticks*100}ms ✓"
    )


# ---------------------------------------------------------------
# TEST 8 — DISPLAY: all 4 LEDs flash
# ---------------------------------------------------------------
@cocotb.test()
async def test_08_display_leds_flash(dut):
    """In DISPLAY all 4 LEDs must toggle together (flash_ctrl)."""
    dut._log.info("Test 08: DISPLAY LEDs flash")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)
    await press_button(dut, led_to_btn(lit))
    await ClockCycles(dut.clk, 10)

    snap1 = int(dut.uio_out.value) & 0xF0
    await ClockCycles(dut.clk, FLASH_HALF * 2 + 20)
    snap2 = int(dut.uio_out.value) & 0xF0

    # Should have toggled between 0x00 and 0xF0
    assert snap1 != snap2, \
        f"LEDs did not flash: snap1=0x{snap1:02X} snap2=0x{snap2:02X}"
    dut._log.info(f"PASS: LEDs flashing 0x{snap1:02X}↔0x{snap2:02X}")


# ---------------------------------------------------------------
# TEST 9 — Overflow: counter maxes out, auto enters DISPLAY
# ---------------------------------------------------------------
@cocotb.test()
async def test_09_overflow(dut):
    """If player never reacts, 5-bit counter UTC → auto DISPLAY."""
    dut._log.info("Test 09: counter overflow → auto DISPLAY")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await release_reset(dut)
    await wait_for_react_state(dut)

    # Don't press any button, wait 33 ticks (overflow at 31)
    await ClockCycles(dut.clk, 33 * TICK + 10)

    state = int(dut.user_project.game.state.value)
    assert state == 3, \
        f"Expected DISPLAY (3) after overflow, got state={state}"

    rt = int(dut.user_project.game.react_time_Q.value)
    assert rt == 0b11111, f"Expected max count 31, got {rt}"
    dut._log.info(f"PASS: overflow → DISPLAY, time={rt} (max)")


# ---------------------------------------------------------------
# TEST 10 — uio_oe: upper 4 bits are outputs, lower 4 are inputs
# ---------------------------------------------------------------
@cocotb.test()
async def test_10_uio_oe_direction(dut):
    """uio_oe[7:4] must be 1 (output), uio_oe[3:0] must be 0 (input)."""
    dut._log.info("Test 10: uio_oe direction bits")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await ClockCycles(dut.clk, 3)

    oe = int(dut.uio_oe.value)
    assert (oe & 0xF0) == 0xF0, \
        f"Expected uio_oe[7:4]=0xF, got 0x{(oe>>4):01X}"
    assert (oe & 0x0F) == 0x00, \
        f"Expected uio_oe[3:0]=0x0, got 0x{(oe&0xF):01X}"
    dut._log.info(f"PASS: uio_oe=0x{oe:02X} (upper=outputs, lower=inputs)")


# ---------------------------------------------------------------
# TEST 11 — rst_n from DISPLAY returns to IDLE
# ---------------------------------------------------------------
@cocotb.test()
async def test_11_reset_from_display(dut):
    """Asserting rst_n in DISPLAY must return to IDLE with dash on 7-seg."""
    dut._log.info("Test 11: reset from DISPLAY → IDLE")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)
    await press_button(dut, led_to_btn(lit))
    await ClockCycles(dut.clk, 10)

    assert int(dut.user_project.game.state.value) == 3, "Should be in DISPLAY"

    # Reset
    await do_reset(dut)
    await ClockCycles(dut.clk, 3)

    state = int(dut.user_project.game.state.value)
    seg   = int(dut.uo_out.value)
    leds  = int(dut.uio_out.value) & 0xF0

    assert state == 0,          f"Expected IDLE (0), got state={state}"
    assert seg   == SEG_DASH,   f"Expected dash 0x{SEG_DASH:02X}, got 0x{seg:02X}"
    assert leds  == 0x00,       f"Expected LEDs off, got 0x{leds:02X}"
    dut._log.info("PASS: reset from DISPLAY → IDLE, dash on 7-seg, LEDs off")


# ---------------------------------------------------------------
# TEST 12 — Two rounds produce different random target LEDs
# ---------------------------------------------------------------
@cocotb.test()
async def test_12_two_rounds_different_led(dut):
    """LFSR should pick a different target LED across two rounds."""
    dut._log.info("Test 12: two rounds, LFSR diversity")
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    # Round 1
    await do_reset(dut)
    await release_reset(dut)
    led1 = await wait_for_react_state(dut)
    dut._log.info(f"Round 1 LED: 0x{led1:02X}")
    await press_button(dut, led_to_btn(led1))
    await ClockCycles(dut.clk, 5)

    # Round 2
    await do_reset(dut)
    await release_reset(dut)
    led2 = await wait_for_react_state(dut)
    dut._log.info(f"Round 2 LED: 0x{led2:02X}")

    # Not a hard failure if same (LFSR could land same), just informational
    if led1 != led2:
        dut._log.info(f"PASS: different LEDs rounds 1 vs 2 ✓")
    else:
        dut._log.warning(
            f"Same LED both rounds (0x{led1:02X}) — rare but possible with LFSR"
        )

    # Hard assert: LED must always be exactly one of the 4 valid options
    assert led2 in LEDS, \
        f"Round 2 LED 0x{led2:02X} is not a valid target LED!"
    dut._log.info("PASS: two-round test complete")
