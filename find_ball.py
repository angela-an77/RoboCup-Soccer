# This work is licensed under the MIT license.
# Copyright (c) 2013-2023 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE
#
# Multi Color Blob Tracking Example
#
# This example shows off multi color blob tracking using the OpenMV Cam.

import sensor
import time
import math

# Color Tracking Thresholds (L Min, L Max, A Min, A Max, B Min, B Max)
# The below thresholds track in general red/green things. You may wish to tune them...
thresholds = [
    # (30, 100, 15, 127, 15, 127),  # generic_red_thresholds
    # (30, 100, -64, -8, -32, 32),  # generic_green_thresholds
    # (0, 15, 0, 40, -80, -20), # generic_blue_thresholds
    (0, 100, 20, 50, 8, 29), # generic orange
]
# You may pass up to 16 thresholds above. However, it's not really possible to segment any
# scene with 16 thresholds before color thresholds start to overlap heavily.

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

    MAX_ELONGATION = 0.8
    for blob in img.find_blobs(thresholds, pixels_threshold=200, area_threshold=200):
        # These values depend on the blob not being circular - otherwise they will be shaky.
        if blob.elongation() < MAX_ELONGATION:
            img.draw_edges(blob.min_corners(), color=(255, 0, 0))
            img.draw_line(blob.major_axis_line(), color=(0, 255, 0))
            img.draw_line(blob.minor_axis_line(), color=(0, 0, 255))
        # These values are stable all the time.
        img.draw_rectangle(blob.rect())
        img.draw_cross(blob.cx(), blob.cy())
        # Note - the blob rotation is unique to 0-180 only.
        img.draw_keypoints(
            [(blob.cx(), blob.cy(), int(math.degrees(blob.rotation())))], size=20
        )
    #print(clock.fps())

