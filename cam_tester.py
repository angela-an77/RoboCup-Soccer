# Camera "publisher/subscriber" - By: soccerpi2 - Fri Mar 6 2026

import sensor
# import image
import time
# import math
import pyb

# Color Tracking Thresholds (L Min, L Max, A Min, A Max, B Min, B Max)
thresholds = {
    "yellow": (0, 100, -128, 127, 19, 127), # yellow goal threshold
    "blue": (0, 67, -128, 32, -128, -10), # blue goal threshold
    "orange": (36, 100, 24, 93, -9, 72), # orange ball threshold
}

orange = thresholds.get("orange")
yellow = thresholds.get("yellow")
blue = thresholds.get("blue")

sensor.reset() # Reset and initialize the sensor.
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (or GRAYSCALE)
sensor.set_framesize(sensor.QVGA) # Set frame size to QVGA (320x240)
sensor.skip_frames(time=2000) # Wait for settings take effect
sensor.set_auto_exposure(False, exposure_us=13500)
sensor.set_auto_gain(False)  # must be turned off for color tracking
sensor.set_auto_whitebal(False)  # must be turned off for color tracking
sensor.set_saturation(3)
sensor.set_brightness(2)

img = sensor.snapshot()
img_cx = sensor.width() // 2
img_cy = sensor.height() // 2

# LEDs
r = pyb.LED(1)
g = pyb.LED(2)
b = pyb.LED(3)

time.sleep(2)

# None if we have to determine goal in game, color if
goal_color = None


def establish_goal(img):

    global goal_color

    MIN_GOAL_AREA = 1000

    yellow_blobs = img.find_blobs([yellow], pixels_threshold=200, area_threshold=200)
    blue_blobs = img.find_blobs([blue], pixels_threshold=200, area_threshold=200)

    best_yellow = max(yellow_blobs, key=lambda b: b.area()) if yellow_blobs else None
    best_blue = max(blue_blobs, key=lambda b: b.area()) if blue_blobs else None

    if best_yellow and best_blue:
        goal_color = 'yellow' if best_yellow.area() > best_blue.area() else 'blue'
    elif best_yellow:
        goal_color = 'yellow'
    elif best_blue:
        goal_color = 'blue'

    print(goal_color)

if goal_color is None:
    establish_goal(img)

def search_ball(img):

    MAX_BALL_ELONGATION = 0.5

    max_blob = None

    for blob in img.find_blobs([orange], pixels_threshold=200, area_threshold=200):
        if blob.elongation() < MAX_BALL_ELONGATION:
            if max_blob == None or blob.area() > max_blob.area():
                max_blob = blob

    if max_blob == None:
        r.on()
        g.off()
        b.off()
        return 'no ball'

    else:
        r.on()
        g.off()
        b.on()

        ball_box = max_blob.rect()
        img.draw_rectangle(ball_box, color=(255, 165, 0))

        ball_cx = max_blob.cx()
        # ball_cy = blob.cy()
        img.draw_cross(max_blob.cx(), max_blob.cy())

        # Note - the blob rotation is unique to 0-180 only.
        """
        img.draw_keypoints(
            [(blob.cx(), blob.cy(), int(math.degrees(blob.rotation())))], size=20
        )
        """

        diff = ball_cx - img_cx
        # ball is centered
        if abs(diff) < 10:
            return 'ball|center'
        else:
            # spin left
            if diff < 0:
                return 'ball|left'
            # spin right
            else:
                return 'ball|right'


def search_goal(img):

    MIN_GOAL_ELONGATION = 0.1
    MAX_GOAL_ELONGATION = 0.9

    global goal_color
    print(goal_color)
    blobs = None

    if goal_color == 'yellow':
        outline = (255, 255, 0)
        blobs = img.find_blobs([yellow], pixels_threshold=200, area_threshold=200)

    elif goal_color == 'blue':
        outline = (0, 0, 255)
        blobs = img.find_blobs([blue], pixels_threshold=200, area_threshold=200)

    max_blob = None
    if blobs is not None:
        for blob in blobs:
            # box = blob.rect()
            # img.draw_rectangle(box)
            if MIN_GOAL_ELONGATION < blob.elongation() < MAX_GOAL_ELONGATION:
                if max_blob == None or blob.area() > max_blob.area():
                    max_blob = blob

    if max_blob == None:
        print('SPIN')
        r.on()
        g.off()
        b.off()
        send_msg('no goal|')


    else:
        r.on()
        g.off()
        b.on()

        goal_box = max_blob.rect()
        # goal_box_center = (blob.cx(), blob.cy())
        print(goal_box)
        img.draw_rectangle(goal_box, color=outline)

        goal_cx = max_blob.cx()
        # ball_cy = blob.cy()

        img.draw_cross(max_blob.cx(), max_blob.cy())
        # Note - the blob rotation is unique to 0-180 only.
        """
        img.draw_keypoints(
            [(blob.cx(), blob.cy(), int(math.degrees(blob.rotation())))], size=20
        )
        """

        diff = goal_cx - img_cx
        # ball is centered
        if abs(diff) < 20:
            send_msg('goal|center')
        else:
            # spin left
            if diff < 0:
                send_msg('goal|left')
            # spin right
            else:
                send_msg('goal|right')

def send_msg(pub_msg):
    #usb.write(pub_msg + "\n")
    print(pub_msg)

while True:

    clock = time.clock()
    clock.tick()

    img = sensor.snapshot()


    search_ball(img)
    search_goal(img)

    time.sleep_ms(50)
