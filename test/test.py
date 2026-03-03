import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

@cocotb.test()
async def test_reaction_game(dut):
    # Setup clock
    cocotb.start_soon(Clock(dut.clk, 40, "ns").start())

    # Helper to reset
    dut.rst_n.value = 0
    dut.ena.value = 1
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # Access the FSM via the instance name 'game' inside 'user_project'
    fsm = dut.user_project.game

    # 1. Verify IDLE
    # Note: Accessing state register directly
    assert int(fsm.state.value) == 0, f"Expected IDLE(0), got {fsm.state.value}"
    dut._log.info("IDLE state verified")

    # 2. Verify WAIT transition
    await ClockCycles(dut.clk, 10)
    assert int(fsm.state.value) == 1, f"Expected WAIT(1), got {fsm.state.value}"
    dut._log.info("WAIT state verified")

    # 3. Verify LFSR
    # Path: user_project -> game -> lfsr_inst -> rnd
    val1 = int(fsm.lfsr_inst.rnd.value)
    await ClockCycles(dut.clk, 5)
    val2 = int(fsm.lfsr_inst.rnd.value)
    assert val1 != val2, "LFSR not advancing"
    dut._log.info("LFSR advancing verified")

    dut._log.info("Basic connectivity verified!")
