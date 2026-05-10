import sensor
import time
import pyb
from pyb import Pin

thresholds = {
    "yellow": (0, 100, -128, 127, 19, 127),
    "blue": (0, 67, -128, 32, -128, -10),
    "orange": (43, 100, 16, 69, -11, 58),
}

orange = thresholds.get("orange")
yellow = thresholds.get("yellow")
blue = thresholds.get("blue")

switch = Pin('P0', Pin.IN, Pin.PULL_DOWN)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_windowing((0, 100, 320, 140))
sensor.skip_frames(time=2000)
sensor.set_auto_exposure(False, exposure_us=13500)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.set_saturation(3)
sensor.set_brightness(2)

img = sensor.snapshot()
img_cx = sensor.width() // 2
img_cy = sensor.height() // 2

r = pyb.LED(1)
g = pyb.LED(2)
b = pyb.LED(3)

usb = pyb.USB_VCP()
buffer = ""
time.sleep(2)

# Can probably set to None but test
goal_color = 'blue'

def send_msg(pub_msg):
    usb.write(pub_msg + "\n")


def search_ball(img):
    MAX_BALL_ELONGATION = 0.7
    max_blob = None

    for blob in img.find_blobs([orange], pixels_threshold=10, area_threshold=10):
        if blob.elongation() < MAX_BALL_ELONGATION:
            if max_blob == None or blob.area() > max_blob.area():
                max_blob = blob

    if max_blob == None:
        r.off()
        g.off()
        b.on()
        send_msg('no ball|')

    else:
        # ball_box = max_blob.rect()
        # img.draw_rectangle(goal_box, color=outline)
        # img.draw_cross(max_blob.cx(), max_blob.cy())

        ball_cx = max_blob.cx()
        diff = ball_cx - img_cx
        # print(diff)

        if abs(diff) < 30:
            r.off()
            g.on()
            b.off()
            send_msg('ball|forward')
            # add condition for dribble send_msg('ball|dribble')
        else:
            r.on()
            g.off()
            b.on()
            if diff < 0:
                send_msg('ball|left')
            else:
                send_msg('ball|right')


def search_goal(img):
    global goal_color
    #print(goal_color)

    MIN_GOAL_ELONGATION = 0.1
    MAX_GOAL_ELONGATION = 0.9
    min_goal_area = 100

    max_blob = None
    if goal_color == 'yellow':
        outline = (255, 255, 0)
        for blob in img.find_blobs([yellow], pixels_threshold=200, area_threshold=200):
            if MIN_GOAL_ELONGATION < blob.elongation() < MAX_GOAL_ELONGATION:
                if max_blob == None or blob.area() > max_blob.area():
                    max_blob = blob

    elif goal_color == 'blue':
        outline = (0, 0, 255)
        for blob in img.find_blobs([blue], pixels_threshold=200, area_threshold=200):
            if MIN_GOAL_ELONGATION < blob.elongation() < MAX_GOAL_ELONGATION:
                if max_blob == None or blob.area() > max_blob.area():
                    max_blob = blob

    if blobs is not None:
        for blob in blobs:
            if MIN_GOAL_ELONGATION < blob.elongation() < MAX_GOAL_ELONGATION:
                if max_blob == None or blob.area() > max_blob.area():
                    max_blob = blob

    if max_blob == None:
        r.on()
        g.off()
        b.off()
        send_msg('no goal|right')

    else:
        r.on()
        g.off()
        b.on()

        # goal_box = max_blob.rect()
        # img.draw_rectangle(goal_box, color=outline)
        # img.draw_cross(max_blob.cx(), max_blob.cy())

        goal_leftx = max_blob.x()
        goal_rightx = max_blob.x() + max_blob.w()

        diff_left = img_cx - goal_leftx
        diff_right = img_cx - goal_rightx

        if abs(diff_left) > 30 and abs(diff_right) > 30:
            if max_blob.area() < min_goal_area:
                send_msg('goal|forward')
            else:
                send_msg('goal|shoot')

        else:
            if abs(diff_left) < 30:
                send_msg('goal|right')

            elif abs(diff_right) < 30:
                send_msg('goal|left')

while True:
    # clock = time.clock()
    # clock.tick()

    img = sensor.snapshot()

    is_switched = switch.value() == 1
    if is_switched:
        goal_color = 'yellow'
    else:
        goal_color = 'blue'

    search_ball(img)

    if usb.isconnected() and usb.any():
        r.on()
        g.on()
        b.on()
        sub_data = usb.read().decode()
        buffer += sub_data
        if "\n" in buffer:
            msg, buffer = buffer.split("\n", 1)
            stage = msg.strip()
            if stage in ['SEARCH_GOAL', 'APPROACH_GOAL', 'SHOOT']:
                search_goal(img)

    time.sleep_ms(50)
