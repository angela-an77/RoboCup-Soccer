import sensor
import time
import pyb
from pyb import Pin

thresholds = {
    "yellow": (34, 76, 0, 29, 26, 60),
    "blue": (38, 51, -11, 10, -47, -8),
    "orange": (34, 86, 22, 127, -7, 127),
    "white": (42, 100, 2, 35, -39, 2)
}

orange = thresholds.get("orange")
yellow = thresholds.get("yellow")
blue = thresholds.get("blue")
white = thresholds.get("white")

switch = Pin('P0', Pin.IN, Pin.PULL_DOWN)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
# sensor.set_windowing((0, 0, 320, 260))
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
goal_color = None

# if True, line too close
line = False

def send_msg(pub_msg):
    usb.write(pub_msg + "\n")


def search_ball(img):
    MAX_BALL_ELONGATION = 0.95
    max_blob = None

    for blob in img.find_blobs([orange], pixels_threshold=10, area_threshold=10):
        # print(blob.elongation())
        if blob.elongation() < MAX_BALL_ELONGATION:
            if max_blob == None or blob.area() > max_blob.area():
                max_blob = blob

    if max_blob == None:
        r.off()
        g.off()
        b.on()
        return 'no ball|'

    else:
        ball_box = max_blob.rect()
        img.draw_rectangle(ball_box)
        img.draw_cross(max_blob.cx(), max_blob.cy())

        ball_cx = max_blob.cx()
        diff = ball_cx - img_cx
        # print(diff)
        # print(max_blob.y())
        if abs(diff) < 30:
            if max_blob.y() >= 220:
                return 'ball|dribble'
                r.on()
                g.on()
                b.on()
            else:
                r.off()
                g.on()
                b.off()
                return 'ball|forward'
        else:
            r.on()
            g.off()
            b.on()
            # print(max_blob.area())
            if diff < 0:
                return 'ball|left'
            else:
                return 'ball|right'


def search_goal(img):
    global goal_color
    #print(goal_color)

    min_goal_area = 100

    max_blob = None
    if goal_color == 'yellow':
        outline = (255, 255, 0)
        for blob in img.find_blobs([yellow], pixels_threshold=10, area_threshold=10):
            if 0.8 < blob.elongation():
                if max_blob == None or blob.area() > max_blob.area():
                    max_blob = blob

    elif goal_color == 'blue':
        outline = (0, 0, 255)
        for blob in img.find_blobs([blue], pixels_threshold=10, area_threshold=10):
            # print(blob.elongation())
            if 0.8 < blob.elongation():
                if max_blob == None or blob.area() > max_blob.area():
                    max_blob = blob

    #goal_box = max_blob.rect()
    #img.draw_rectangle(goal_box, color=outline)
    #img.draw_cross(max_blob.cx(), max_blob.cy())
    # print(max_blob.area())

    if max_blob == None:
        # r.on()
        # g.off()
        # b.off()
        return 'no goal|right'

    else:
        # r.on()
        # g.off()
        # b.on()

        goal_leftx = max_blob.x()
        goal_rightx = max_blob.x() + max_blob.w()

        diff_left = img_cx - goal_leftx
        diff_right = img_cx - goal_rightx
        # print(diff_left, diff_right)

        if diff_left > 10 and diff_right < -10:
            if max_blob.area() < min_goal_area:
                return 'goal|forward'
            else:
                return 'goal|shoot'

        elif diff_left <= 0:
            return 'goal_right'
        elif diff_right >= 0:
            return 'goal|left'
        else:
            if abs(diff_left) < abs(diff_right):
                return 'goal|right'

            else:
                return 'goal|left'

def check_line(img):
    global line
    MIN_LINE_ELONGATION = 0.9
    max_blob = None
    roi = (100, 220, 170, 20)

    for blob in img.find_blobs([white], roi=roi, pixels_threshold=100, area_threshold=100):
        # print(blob.elongation())
        # if blob.elongation() > MIN_LINE_ELONGATION:
        # if blob.x() >= img_cx - 100 and blob.x() + blob.w() <= img_cx + 100:
        if max_blob == None or blob.area() > max_blob.area():
            max_blob = blob

    if max_blob != None:
        #line_box = max_blob.rect()
        #img.draw_rectangle(line_box)
        #img.draw_cross(max_blob.cx(), max_blob.cy())

        # bottom of box
        line_cy = max_blob.y() + max_blob.h()
        # print(sensor.height(), line_cy)
        if line_cy == sensor.height():
            line = True
        else:
            line = False
    else:
        line = False

stage = 'SEARCH_BALL'
while True:
    # clock = time.clock()
    # clock.tick()
    ball_msg = 'no ball|forward'
    goal_msg = 'no goal|right'

    img = sensor.snapshot()

    is_switched = switch.value() == 1
    if is_switched:
        goal_color = 'yellow'
    else:
        goal_color = 'blue'

    check_line(img)
    ball_msg = search_ball(img)
    goal_msg = search_goal(img)

    if usb.isconnected() and usb.any():
        r.on()
        g.on()
        b.on()
        sub_data = usb.read().decode()
        buffer += sub_data
        if "\n" in buffer:
            msg, buffer = buffer.split("\n", 1)
            stage = msg.strip()
    # stage = 'SEARCH_GOAL'
    if line:
        if ball_msg == 'ball|dribble' and goal_msg == 'goal|shoot':
            send_msg(goal_msg)
        else:
            send_msg('back|')
    else:
        send_msg(ball_msg)
        if stage in ['SEARCH_GOAL', 'APPROACH_GOAL', 'SHOOT']:
            send_msg(goal_msg)

    time.sleep_ms(50)
