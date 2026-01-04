import os
import time
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

LEFT_STICK_CHANNEL = MCP.P0
RIGHT_STICK_CHANNEL = MCP.P1

class JoySticks():
    def __init__(self):
        # ADC related things

        # make spi bus
        self.spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

        # create the cs (chip select)
        self.cs = digitalio.DigitalInOut(board.D22)

        # create the mcp object
        mcp = MCP.MCP3008(self.spi, self.cs)

        # create analog input channels
        self.left_stick = AnalogIn(self.mcp, LEFT_STICK_CHANNEL)
        self.right_stick = AnalogIn(self.mcp, RIGHT_STICK_CHANNEL)

    def get_left_joystick(self):
        return self.left_stick.value

    def get_right_joystick(self):
        return self.right_stick.value  




    