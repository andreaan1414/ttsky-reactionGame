<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

Here is my implementation of a small reaction game. When the go button is pressed, a random value from an LFSR will be generated and it will light up a random LED from 4-7 and will run a timer in the back end to record how long it takes the player to press the corresponding button (4-7). The result is then displayed on the 7 seg display and all LEDs flash. To redo the game, press the reset button and rhen go button. 
## How to test

The testbench runs 12 cocotb tests. Test 1 checks that after holding rst_n low the 7 segment display shows a dash and all LEDs are off, test 2 confirms that releasing rst_n correctly transitions the FSM from IDLE into WAIT, and test 3 verifies the LFSR module to verify it produces correct random values. 

Test 4 waits for the random delay to expire and checks that exactly one of the four target LEDs lights up in REACT state by  checking if the LED pattern is a power of two, meaning only one bit is set. 
Test 5 test is a button that doesn't match the lit LED and asserts that the FSM stays in REACT, confirming the ignore logic works correctly.
Test 6 presses the correct matching button and verifies the FSM transitions to DISPLAY.
Test 7 reacts after exactly 3 ticks, then waits for the flash cycle to be in its off phase so the segments are unmasked, and checks that uo_out shows the digit 3 with the decimal point lit. 
Test 8 takes two snapshots of the LED outputs separated by more than one full flash period and asserts they differ, confirming the flash controller is toggling all four LEDs together.
Test 9 chekcs 5 bit counter overflows at 31 and the FSM auto-transitions to DISPLAY without any button press. 
Test 10 checks the uio_oe register directly to confirm the upper 4 bidir pins are configured as outputs for the LEDs and the lower 4 are inputs.
Test 11 resets from inside DISPLAY and verifies the system cleanly returns to IDLE with the dash back on the 7 seg and all LEDs off. 
Test 12 plays two full rounds and checks that the LFSR produces a valid target LED both times, and logs whether the two rounds picked different LEDs to demonstrate the randomness working across games.

## External hardware

To play this game you need an LED Display and a 7 Segment display and 8 buttons. 
