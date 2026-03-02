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
# Timing constants (must match Makefile -D overrides)
# TICK_PERIOD    = 100  cycles per 100ms tick
# WAIT_BLINK_PER = 200  cycles per blink half-period
# FLASH_HALF     = 200  cycles per flash half-period
# Max LFSR wait  = 63 ticks × 100 cycles = 6300 cycles
# ---------------------------------------------------------------
TICK        = 100
FLASH_HALF  = 200
MAX_WAIT_CY = 6300   # worst-case LFSR wait (63 ticks × TICK)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

async def do_reset(dut):
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 2)


async def press_go(dut):
    """Pulse go_btn (ui_in[0]) for one cycle."""
    dut.ui_in.value = 0x01
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0x00
    await ClockCycles(dut.clk, 1)


async def press_react(dut):
    """Pulse react_btn (ui_in[1]) for one cycle."""
    dut.ui_in.value = 0x02
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0x00
    await ClockCycles(dut.clk, 1)


async def wait_for_react_state(dut):
    """Block until uo_out == 0x80 (target LED on = REACT state)."""
    for _ in range(MAX_WAIT_CY + 500):
        await RisingEdge(dut.clk)
        if int(dut.uo_out.value) == 0x80:
            return
    raise AssertionError(
        f"Timed out waiting for REACT state. Last uo_out=0x{int(dut.uo_out.value):02X}"
    )



# TEST 1 — Reset: LEDs off, IDLE state

@cocotb.test()
async def test_01_reset(dut):
    """After rst_n goes low then high, uo_out must be 0x00."""
    dut._log.info("Test 01: reset → IDLE")
    clock = Clock(dut.clk, 40, units="ns")   # 25 MHz
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await ClockCycles(dut.clk, 3)

    assert dut.uo_out.value == 0x00, \
        f"Expected uo_out=0x00 after reset, got 0x{int(dut.uo_out.value):02X}"
    dut._log.info("PASS: uo_out=0x00 after reset")



# TEST 2 — IDLE holds without go_btn
@cocotb.test()
async def test_02_idle_no_spurious_start(dut):
    """Design must stay in IDLE (uo_out=0x00) without go_btn."""
    dut._log.info("Test 02: IDLE holds without go_btn")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await ClockCycles(dut.clk, 300)

    assert dut.uo_out.value == 0x00, \
        f"Left IDLE unexpectedly: uo_out=0x{int(dut.uo_out.value):02X}"
    dut._log.info("PASS: stayed in IDLE for 300 cycles without go_btn")



# TEST 3 — LFSR advances and stays non-zero

@cocotb.test()
async def test_03_lfsr_non_zero(dut):
    """LFSR rnd register must be non-zero and change each cycle."""
    dut._log.info("Test 03: LFSR non-zero and advancing")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)

    samples = []
    for _ in range(20):
        await RisingEdge(dut.clk)
        val = int(dut.user_project.game.lfsr_inst.rnd.value)
        samples.append(val)
        assert val != 0, "LFSR locked at 0x00 (stuck in zero state!)"

    unique = len(set(samples))
    assert unique > 1, f"LFSR did not advance — only {unique} distinct value(s) in 20 cycles"
    dut._log.info(f"PASS: LFSR produced {unique} distinct values in 20 cycles")


# TEST 4 — countUD5L counts up correctly

@cocotb.test()
async def test_04_counter_counts_up(dut):
    """
    Verify countUD5L increments by 1 each TICK_PERIOD cycles.
    We get into REACT state so the counter runs, then check two
    consecutive tick boundaries.
    """
    dut._log.info("Test 04: counter increments per tick in REACT state")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await press_go(dut)
    await wait_for_react_state(dut)   # now in REACT, counter running

    # Align to a tick boundary then sample twice
    await ClockCycles(dut.clk, TICK + 2)
    v1 = int(dut.user_project.game.react_time_Q.value)
    await ClockCycles(dut.clk, TICK)
    v2 = int(dut.user_project.game.react_time_Q.value)

    assert v2 == v1 + 1, \
        f"Counter did not increment by 1: v1={v1}, v2={v2}"
    dut._log.info(f"PASS: counter {v1} → {v2} (+1 per tick)")



# TEST 5 — FA/add5/AddSub5: count sequence 0→1→2→3

@cocotb.test()
async def test_05_adder_sequence(dut):
    """
    The adder chain (FA→add5→AddSub5) inside countUD5L must produce
    the sequence 0, 1, 2, 3 over consecutive ticks.
    """
    dut._log.info("Test 05: adder count sequence 0→1→2→3")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)

    # Counter should be 0 in IDLE (LD held high with Din=0)
    v0 = int(dut.user_project.game.react_time_Q.value)
    assert v0 == 0, f"Counter not 0 in IDLE, got {v0}"

    await press_go(dut)
    await wait_for_react_state(dut)

    seq = []
    for _ in range(4):
        await ClockCycles(dut.clk, TICK)
        seq.append(int(dut.user_project.game.react_time_Q.value))

    dut._log.info(f"Sequence: {seq}")
    for i in range(1, len(seq)):
        assert seq[i] == seq[i-1] + 1, \
            f"Adder error at step {i}: expected {seq[i-1]+1}, got {seq[i]}"
    dut._log.info("PASS: adder sequence correct")



# TEST 6 — flash_ctrl toggles output in DISPLAY state

@cocotb.test()
async def test_06_flash_ctrl_toggles(dut):
    """flash_ctrl must toggle flash_out at least 3 times in DISPLAY."""
    dut._log.info("Test 06: flash_ctrl toggles")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await press_go(dut)
    await wait_for_react_state(dut)
    await press_react(dut)
    await ClockCycles(dut.clk, 5)

    transitions = 0
    last = int(dut.user_project.game.flash_inst.flash_out.value)
    for _ in range(FLASH_HALF * 8):
        await RisingEdge(dut.clk)
        cur = int(dut.user_project.game.flash_inst.flash_out.value)
        if cur != last:
            transitions += 1
            last = cur
        if transitions >= 3:
            break

    assert transitions >= 3, \
        f"flash_ctrl only toggled {transitions} time(s), expected ≥ 3"
    dut._log.info(f"PASS: flash_ctrl toggled {transitions} times")


# TEST 7 — go_btn → WAIT state

@cocotb.test()
async def test_07_go_btn_starts_wait(dut):
    """Pressing go_btn from IDLE must enter WAIT (get-ready blink on bit 0)."""
    dut._log.info("Test 07: go_btn → WAIT")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await press_go(dut)
    await ClockCycles(dut.clk, 2)

    state = int(dut.user_project.game.state.value)
    assert state == 1, f"Expected WAIT (1), got state={state}"
    dut._log.info("PASS: entered WAIT after go_btn")



# TEST 8 — WAIT → REACT (random delay expires, target LED on)

@cocotb.test()
async def test_08_wait_to_react(dut):
    """After random delay, bit 7 of uo_out must be solid high (REACT)."""
    dut._log.info("Test 08: WAIT → REACT after random delay")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await press_go(dut)
    await wait_for_react_state(dut)   # waits up to MAX_WAIT_CY

    assert int(dut.uo_out.value) == 0x80, \
        f"Expected uo_out=0x80 in REACT, got 0x{int(dut.uo_out.value):02X}"
    dut._log.info(f"PASS: target LED on, rand_wait was "
                  f"{int(dut.user_project.game.rand_wait.value)} ticks")



# TEST 9 — react_btn → DISPLAY, reaction time in uo_out[4:0]

@cocotb.test()
async def test_09_react_btn_captures_time(dut):
    """
    React exactly N ticks after target LED lights.
    uo_out[4:0] in DISPLAY (when flash=0) must equal N.
    """
    dut._log.info("Test 09: react_btn captures correct reaction time")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await press_go(dut)
    await wait_for_react_state(dut)

    expected = 3   # react after 3 ticks = 300ms
    await ClockCycles(dut.clk, expected * TICK + 2)
    await press_react(dut)
    await ClockCycles(dut.clk, 5)

    # Spin until flash_out=0 so the time bits are unmasked
    for _ in range(FLASH_HALF * 3):
        await RisingEdge(dut.clk)
        if int(dut.user_project.game.flash_inst.flash_out.value) == 0:
            break

    leds = int(dut.uo_out.value)
    time_bits = leds & 0x1F

    assert time_bits == expected, \
        f"Expected reaction time={expected} ticks, got {time_bits} " \
        f"(uo_out=0x{leds:02X})"
    dut._log.info(f"PASS: reaction time = {time_bits} ticks ({time_bits*100}ms)")



# TEST 10 — DISPLAY: uo_out actually flashes (changes value)

@cocotb.test()
async def test_10_display_leds_flash(dut):
    """uo_out must change during DISPLAY state (flash XOR toggling)."""
    dut._log.info("Test 10: DISPLAY LEDs flash")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await press_go(dut)
    await wait_for_react_state(dut)
    await press_react(dut)
    await ClockCycles(dut.clk, 10)

    snap1 = int(dut.uo_out.value)
    await ClockCycles(dut.clk, FLASH_HALF * 2 + 20)
    snap2 = int(dut.uo_out.value)

    assert snap1 != snap2, \
        f"LEDs did not flash: snap1=0x{snap1:02X} snap2=0x{snap2:02X}"
    dut._log.info(f"PASS: LED flash detected 0x{snap1:02X} → 0x{snap2:02X}")



# TEST 11 — Overflow: no button press, auto-transition at 31 ticks

@cocotb.test()
async def test_11_overflow_auto_display(dut):
    """
    If the player never presses react_btn, the 5-bit counter overflows
    at 31 and the FSM must automatically enter DISPLAY.
    """
    dut._log.info("Test 11: overflow auto-transition to DISPLAY")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await press_go(dut)
    await wait_for_react_state(dut)

    # Wait 33 ticks without pressing react (counter rolls over at 31)
    await ClockCycles(dut.clk, 33 * TICK + 10)

    state = int(dut.user_project.game.state.value)
    assert state == 3, \
        f"Expected DISPLAY (3) after overflow, got state={state}"

    rt = int(dut.user_project.game.react_time_Q.value)
    assert rt == 0b11111, \
        f"Expected max reaction time 31 (0b11111), got {rt}"
    dut._log.info(f"PASS: auto-transitioned to DISPLAY, time={rt} (max/overflow)")



# TEST 12 — Reset from DISPLAY returns to IDLE

@cocotb.test()
async def test_12_reset_from_display(dut):
    """rst_n low while in DISPLAY must cleanly return to IDLE."""
    dut._log.info("Test 12: reset from DISPLAY → IDLE")
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    await do_reset(dut)
    await press_go(dut)
    await wait_for_react_state(dut)
    await press_react(dut)
    await ClockCycles(dut.clk, 10)

    assert int(dut.user_project.game.state.value) == 3, "Should be in DISPLAY"

    # Now reset
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    state = int(dut.user_project.game.state.value)
    leds  = int(dut.uo_out.value)

    assert state == 0, f"Expected IDLE (0) after reset, got state={state}"
    assert leds  == 0x00, f"Expected uo_out=0x00 after reset, got 0x{leds:02X}"
    dut._log.info("PASS: reset from DISPLAY → IDLE, leds=0x00")
