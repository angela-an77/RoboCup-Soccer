# Untitled - By: soccerpi2 - Mon Mar 2 2026

from machine import I2C
import time
import bno055

# Initialize IMU
i2c = I2C(2)
imu = bno055.BNO055(i2c)

time.sleep(1) # allow sensor to stabilize

# Store starting orientation
start_heading, _, _ = imu.euler()


def get_displacement():
    current_heading, _, _ = imu.euler()

    delta = current_heading - start_heading

    # Normalize to [-180, 180]
    if delta > 180:
        delta -= 360
    elif delta < -180:
        delta += 360

    return delta

while True:
    angle = get_displacement()
    print("Displacement:", angle)
    time.sleep(0.1)
