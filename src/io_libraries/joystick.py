from gpiozero import PWMLED, MCP3008

LEFT_STICK_X_CHANNEL = 0
LEFT_STICK_Y_CHANNEL = 1
RIGHT_STICK_X_CHANNEL = 2
RIGHT_STICK_Y_CHANNEL = 3

class JoySticks():
    def __init__(self):
        # ADC output stuff

        self.left_x = MCP3008(LEFT_STICK_X_CHANNEL)
        self.left_y = MCP3008(LEFT_STICK_Y_CHANNEL)
        self.right_x = MCP3008(RIGHT_STICK_X_CHANNEL)
        self.right_y = MCP3008(RIGHT_STICK_Y_CHANNEL)

    def get_left_joystick(self):
        return [self.left_x.value, self.left_y.value]

    def get_right_joystick(self):
        return [self.right_x.value, self.right_y.value] 


