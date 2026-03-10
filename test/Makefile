# See https://docs.cocotb.org/en/stable/quickstart.html for more info

SIM ?= icarus
FST ?= -fst
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src

PROJECT_SOURCES  = fa.v
PROJECT_SOURCES += mux2to1.v
PROJECT_SOURCES += add5.v
PROJECT_SOURCES += countUD5L.v
PROJECT_SOURCES += lfsr.v
PROJECT_SOURCES += flash.v
PROJECT_SOURCES += hex7seg.v
PROJECT_SOURCES += reaction_fsm.v
PROJECT_SOURCES += tt_um_andreaan1414_top_reaction.v

# Speed-up timing for simulation
COMPILE_ARGS += -DTICK_PERIOD=100
COMPILE_ARGS += -DWAIT_BLINK_PER=200
COMPILE_ARGS += -DFLASH_HALF=200

ifneq ($(GATES),yes)

SIM_BUILD        = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

SIM_BUILD        = sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DUSE_POWER_PINS
COMPILE_ARGS    += -DSIM
COMPILE_ARGS    += -DUNIT_DELAY=\#1
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

endif

COMPILE_ARGS    += -I$(SRC_DIR)
VERILOG_SOURCES += $(PWD)/tb.v
TOPLEVEL         = tb
COCOTB_TEST_MODULES = test

include $(shell cocotb-config --makefiles)/Makefile.sim

