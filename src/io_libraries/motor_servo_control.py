import board
from time import sleep

from adafruit_pca9685 import PCA9685

MOTOR_CHANNEL = 0
SERVO_CHANNEL = 1
PWM_FREQUENCY = 50
PERIOD_OF_FREQ_MICRO_SEC = int((1/PWM_FREQUENCY)*(10**6))

# Intput to PCA9685 module which will define a signal which is always high
DUTY_CYCLE_MAX_VALUE = 0xFFFF

# Pulse length in micro seconds
MAX_THROTTLE_PULSE_LEN = 2000
MIN_THROTTLE_PULSE_LEN = 1000

# Intput to PCA9685 module which will define a pulse of length 1000 microseconds (min throttle)
MIN_PWM_MODULE_INPUT = int(DUTY_CYCLE_MAX_VALUE/PERIOD_OF_FREQ_MICRO_SEC * MIN_THROTTLE_PULSE_LEN)

# Intput to PCA9685 module which will define a pulse of length 2000 microseconds (max throttle)
MAX_PWM_MODULE_INPUT = int(DUTY_CYCLE_MAX_VALUE/PERIOD_OF_FREQ_MICRO_SEC * MAX_THROTTLE_PULSE_LEN)

class Actuation():
    def __init__(self):

        # Setup connection to pwm board 
        self.i2c = board.I2C()
        self.pca = PCA9685(self.i2c)
        self.pca.frequency = PWM_FREQUENCY

        self.motor_speed = 0
        self.servo_angle = 0

        self.pca.channels[MOTOR_CHANNEL].duty_cycle = MIN_THROTTLE_PULSE_LEN
        # self.pca.channels[SERVO_CHANNEL].duty_cycle = self.servo_channel_duty
    
    # Function to set the duty cycle of the motor. Takes a speed value from -1 to 1
    def calc_pwm_value(self, speed):
        PWM_VAL = (MAX_PWM_MODULE_INPUT-MIN_PWM_MODULE_INPUT)*(speed/100) + MIN_PWM_MODULE_INPUT
        print(int(PWM_VAL))
        return int(PWM_VAL)

    def set_motor_speed(self, speed):
        self.pca.channels[MOTOR_CHANNEL].duty_cycle = self.calc_pwm_value(speed)

if __name__ == "__main__":
    motor_control = Actuation()
    speed = 0
    while(True):
        motor_control.set_motor_speed(speed)
        speed = (speed +1) % 100
        sleep(0.01)
