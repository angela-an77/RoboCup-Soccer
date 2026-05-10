from pyb import Pin
import time

switch = Pin('P0', Pin.IN, Pin.PULL_DOWN)

while True:
    is_switched = switch.value() == 1
    print(is_switched)
    time.sleep_ms(500)