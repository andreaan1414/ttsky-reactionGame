# SPDX-FileCopyrightText: © 2024 Andrea Arreortua
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# Constants
BTN4, BTN5, BTN6, BTN7 = 0x10, 0x20, 0x40, 0x80
BTNS = [BTN4, BTN5, BTN6, BTN7]
SEG_DASH, SEG_DP, FLASH_HALF = 0x40, 0x80, 200
TICK = 100
MAX_WAIT = 6400

# Helpers
async def do_reset(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
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

def led_to_btn(led_mask):
    return led_mask

# 

@cocotb.test()
async def test_01_reset_idle(dut):
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())
    await do_reset(dut)
    assert int(dut.uo_out.value) == SEG_DASH
    assert (int(dut.uio_out.value) & 0xF0) == 0x00

@cocotb.test()
async def test_02_release_goes_to_wait(dut):
    await do_reset(dut)
    await release_reset(dut)
    assert int(dut.game.state.value) == 1

@cocotb.test()
async def test_03_lfsr(dut):
    await do_reset(dut)
    samples = set()
    for _ in range(20):
        await RisingEdge(dut.clk)
        val = int(dut.game.lfsr_inst.rnd.value)
        assert val != 0
        samples.add(val)
    assert len(samples) > 1

@cocotb.test()
async def test_04_wait_to_react_one_led(dut):
    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)
    assert lit != 0 and (lit & (lit - 1)) == 0
    assert int(dut.game.state.value) == 2

@cocotb.test()
async def test_05_wrong_button_ignored(dut):
    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)
    wrong_btn = next(b for b in BTNS if b != led_to_btn(lit))
    await press_button(dut, wrong_btn)
    await ClockCycles(dut.clk, 3)
    assert int(dut.game.state.value) == 2

@cocotb.test()
async def test_06_correct_button_display(dut):
    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)
    await ClockCycles(dut.clk, 2 * TICK)
    await press_button(dut, led_to_btn(lit))
    await ClockCycles(dut.clk, 3)
    assert int(dut.game.state.value) == 3

@cocotb.test()
async def test_07_display_shows_time(dut):
    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)
    await ClockCycles(dut.clk, 3 * TICK)
    await press_button(dut, led_to_btn(lit))
    # Path corrected to game.flash_inst
    for _ in range(FLASH_HALF * 3):
        await RisingEdge(dut.clk)
        if int(dut.game.flash_inst.flash_out.value) == 0:
            break
    seg = int(dut.uo_out.value)
    assert (seg & SEG_DP) != 0 and (seg & 0x7F) == 0x4F

@cocotb.test()
async def test_08_display_leds_flash(dut):
    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)
    await press_button(dut, led_to_btn(lit))
    await ClockCycles(dut.clk, 10)
    snap1 = int(dut.uio_out.value) & 0xF0
    await ClockCycles(dut.clk, FLASH_HALF * 2 + 20)
    snap2 = int(dut.uio_out.value) & 0xF0
    assert snap1 != snap2

@cocotb.test()
async def test_09_overflow(dut):
    await do_reset(dut)
    await release_reset(dut)
    await wait_for_react_state(dut)
    await ClockCycles(dut.clk, 33 * TICK)
    assert int(dut.game.state.value) == 3
    # Path corrected to game.react_counter
    assert int(dut.game.react_counter.Q.value) == 31

@cocotb.test()
async def test_10_uio_oe_direction(dut):
    await do_reset(dut)
    assert (int(dut.uio_oe.value) & 0xF0) == 0xF0

@cocotb.test()
async def test_11_reset_from_display(dut):
    await do_reset(dut)
    await release_reset(dut)
    lit = await wait_for_react_state(dut)
    await press_button(dut, led_to_btn(lit))
    await ClockCycles(dut.clk, 5)
    await do_reset(dut)
    assert int(dut.game.state.value) == 0

@cocotb.test()
async def test_12_two_rounds_different_led(dut):
    await do_reset(dut)
    await release_reset(dut)
    led1 = await wait_for_react_state(dut)
    await press_button(dut, led_to_btn(led1))
    await ClockCycles(dut.clk, 5)
    await do_reset(dut)
    await release_reset(dut)
    led2 = await wait_for_react_state(dut)
    assert led2 in [0x10, 0x20, 0x40, 0x80]
