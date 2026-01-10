from joystick import JoySticks
from time import sleep

#create an object called pot that refers to MCP3008 channel 0
sticks = JoySticks()

while True:
    print(sticks.get_right_joystick())
    sleep(0.1)