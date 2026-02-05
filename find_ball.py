# This work is licensed under the MIT license.
# Copyright (c) 2013-2023 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE
#
# Multi Color Blob Tracking Example
#
# This example shows off multi color blob tracking using the OpenMV Cam.

import sensor
import image
import time
import math
from pyb import Servo

# Color Tracking Thresholds (L Min, L Max, A Min, A Max, B Min, B Max)
thresholds = [
    # (30, 100, 15, 127, 15, 127),  # generic_red_thresholds
    # (30, 100, -64, -8, -32, 32),  # generic_green_thresholds
    # (0, 15, 0, 40, -80, -20), # generic_blue_thresholds
    (27, 73, 17, 127, 16, 127), # generic orange
]

ball_box = None
ball_center = None

# Servo setup
pan_servo = Servo(1) # P7
tilt_servo = Servo(2) # P8

pan_angle = 0
tilt_angle = 0

sensor.reset() # Reset and initialize the sensor.
sensor.set_vflip(True)
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA) # Set frame size to QVGA (320x240)
sensor.skip_frames(time=2000) # Wait for settings take effect
sensor.set_auto_exposure(False, exposure_us=13500)
sensor.set_auto_gain(False)  # must be turned off for color tracking
sensor.set_auto_whitebal(False)  # must be turned off for color tracking
sensor.set_saturation(3)
sensor.set_brightness(2)

clock = time.clock()

# Only blobs that with more pixels than "pixel_threshold" and more area than "area_threshold" are
# returned by "find_blobs" below. Change "pixels_threshold" and "area_threshold" if you change the
# camera resolution. Don't set "merge=True" because that will merge blobs which we don't want here.


while True:
    clock.tick()
    img = sensor.snapshot()

    # Image Center
    img_center = (img.width() // 2, img.height() // 2)

    MAX_ELONGATION = 0.5
    for blob in img.find_blobs(thresholds, pixels_threshold=200, area_threshold=200):
        # These values depend on the blob not being circular - otherwise they will be shaky.
        if blob.elongation() < MAX_ELONGATION:
            ball_box = blob.rect()
            ball_center = (blob.cx(), blob.cy())
            img.draw_rectangle(ball_box)
            # img.draw_edges(blob.min_corners(), color=(255, 0, 0))
            # img.draw_line(blob.major_axis_line(), color=(0, 255, 0))
            # img.draw_line(blob.minor_axis_line(), color=(0, 0, 255))
        # These values are stable all the time.
        img.draw_cross(blob.cx(), blob.cy())
        # Note - the blob rotation is unique to 0-180 only.
        """
        img.draw_keypoints(
            [(blob.cx(), blob.cy(), int(math.degrees(blob.rotation())))], size=20
        )
        """

    # Top left corner of ball box
    if ball_box is not None:
        ball_x = ball_box[0]
        ball_y = ball_box[1]
        ball_w = ball_box[2]
        ball_h = ball_box[3]
    else:
        pan_angle = 20
        if pan_angle > 90:
            pan_angle = -pan_angle

        if pan_angle == -90:
            pan_angle -= 20
        elif pan_angle == 90:
            pan_angle += 20


    # Pan and Tilt
    if ball_center is not None:
        x_diff = ball_center[0] - img_center[0]
        y_diff = ball_center[1] - img_center[1]

    if abs(x_diff) > 80:
        if x_diff > 0:
            pan_angle += x_diff * 0.04
        if x_diff < 0:
            pan_angle += x_diff * 0.04

    if abs(y_diff) > 20:
        if y_diff > 0:
            tilt_angle += y_diff * 0.04
        if y_diff < 0:
            tilt_angle += y_diff * 0.04

    print(pan_angle)
    pan_angle = max(-90, min(90, pan_angle))
    pan_servo.angle(pan_angle)
    tilt_angle = max(-90, min(90, tilt_angle))
    tilt_servo.angle(tilt_angle)

    #print(clock.fps())

