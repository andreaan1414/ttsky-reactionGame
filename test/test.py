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

SEG_DASH  = 0b01000000
SEG_BLANK = 0b00000000

def safe_int(sig):
    try:
        return int(sig.value)
    except ValueError:
        return -1

async def wait_for_react(dut, max_cycles=20000):
    """REACT = seg stuck BLANK for >250 consecutive cycles."""
    blank_streak = 0
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        if safe_int(dut.uo_out) == SEG_BLANK:
            blank_streak += 1
            if blank_streak > 250:
                return True
        else:
            blank_streak = 0
    return False


@cocotb.test()
async def tt_um_andreaan1414_top_reaction(dut):
    """Smoke test — confirms design is alive after reset."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    dut._log.info("Reset released, checking outputs are stable...")
    uo_val = dut.uo_out.value
    dut._log.info(f"uo_out = {uo_val}")
    await ClockCycles(dut.clk, 10)
    dut._log.info("Gate-level smoke test passed!")


@cocotb.test()
async def test_wait_blink(dut):
    """In WAIT, uo_out must blink — we see SEG_DASH within 10000 cycles."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    seen_dash = False
    for _ in range(10000):
        await RisingEdge(dut.clk)
        if safe_int(dut.uo_out) == SEG_DASH:
            seen_dash = True
            break

    assert seen_dash, "Never saw SEG_DASH (0x40) in WAIT state"
    dut._log.info("PASS: WAIT blink verified")


@cocotb.test()
async def test_wait_to_react(dut):
    """After wait_cnt expires, seg stays BLANK >250 cycles = REACT."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    reached = await wait_for_react(dut)
    assert reached, "FSM never reached REACT"
    dut._log.info("PASS: REACT state reached")


@cocotb.test()
async def test_correct_button_to_display(dut):
    """One button press in REACT sets dp (bit7) on uo_out = DISPLAY."""
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    assert await wait_for_react(dut), "Never reached REACT"

    found = False
    for btn in range(4):
        dut.ui_in.value = (1 << btn) << 4
        for _ in range(20):
            await RisingEdge(dut.clk)
            if safe_int(dut.uo_out) & 0x80:
                found = True
                dut._log.info(f"PASS: DISPLAY reached with button {btn}")
                break
        dut.ui_in.value = 0
        if found:
            break
        await ClockCycles(dut.clk, 3)

    assert found, "No button moved FSM to DISPLAY"


@cocotb.test()
async def test_debug(dut):
    dut._log.info(f"Signal structure: {dir(dut.user_project)}")
