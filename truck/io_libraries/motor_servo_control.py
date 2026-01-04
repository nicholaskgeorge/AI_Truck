import board

from adafruit_pca9685 import PCA9685

MOTOR_CHANNEL = 0
SERVO_CHANNEL = 1
PWM_FREQUENCY = 50
PERIOD_OF_FREQ_MICRO_SEC = int((1/PWM_FREQUENCY)*(10**6))

# Intput to PCA9685 module which will define a pulse of length 2000 microseconds (full throttle)
DUTY_CYCLE_MAX_VALUE = 0xFFFF

# # Intput to PCA9685 module which will define a pulse of length 2000 microseconds (min throttle)
# MIN_PWM_MODULE_INPUT = 

class Actuation():
    def __init__(self):

        # Setup connection to pwm board 
        self.i2c = board.I2C()
        self.pca = PCA9685(self.i2c)
        self.pca.frequency = PWM_FREQUENCY

        # Define input limits
        self.zero_duty_val = 

        # Making both channels and setting the default pwm to 50%
        self.motor_channel_duty = 0x7FFF
        self.servo_channel_duty = 0x7FFF

        self.motor_speed = 0

        pca.channels[MOTOR_CHANNEL].duty_cycle = self.motor_channel_duty
        pca.channels[SERVO_CHANNEL].duty_cycle = self.servo_channel_duty
    
    # Function to set the duty cycle of the motor
    def set_duty(self, channel, duty_cycle):
        desired_duty_cycle = int(DUTY_CYCLE_MAX_VALUE*duty_cycle)

        if desired_duty_cycle > DUTY_CYCLE_MAX_VALUE:
            raise Exception(f"Duty cycle value of {desired_duty_cycle} when requesting {duty_cycle*100}% outside acceptable range.")
        self.motor_channel_duty = desired_duty_cycle
        pca.channels[MOTOR_CHANNEL].duty_cycle = self.motor_channel_duty
