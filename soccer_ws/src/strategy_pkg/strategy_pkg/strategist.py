# import gpiozero.pins.lgpio
# import lgpio

# def __patched_init(self, chip=None):
#     gpiozero.pines.lgpio.LGPIOFactory.__bases__[0].init(self)
#     chip = 0
#     self._handle = lgpio.gpiochip_open(chip)
#     self._chip = chip
#     self.pin_class = gpiozero.pins.lgpio.LGPIOPin

# gpiozero.pins.lgpio.LGPIOFactory.__init__ = __patched_init

import rclpy
from rclpy.node import Node
from gpiozero import Button
from std_msgs.msg import String

button = Button(17, pull_up=True, bounce_time=0.1)

# subscribes to data from all sensors and interprets it, publishes stage to all
class Strategist(Node):
    def __init__(self):
        button.when_pressed = self.on_button_pressed
        super().__init__('strategist')
        
        self.stage = 'SEARCH_BALL'
        self.ready = False
        self.dribble_sent = False

        # data from camera
        self.ball = 'no ball'
        self.ball_dir = 'forward'
        self.goal = 'no goal'
        self.goal_dir = 'right'

        self.in_dribble_mode = False
        self.just_shot = False

        # pubs and subs
        self.stage_publisher = self.create_publisher(String, 'stage', 10)
        self.command_publisher = self.create_publisher(String, 'command', 10)

        self.cam_subscription = self.create_subscription(
            String,
            'cam_msg',
            self.interpret_camera,
            10)

        # run pubs and set stage constantly
        self.stage_timer = self.create_timer(0.05, self.publish_stage)
        self.command_timer = self.create_timer(0.5, self.publish_command)
    
    def on_button_pressed(self):
        self.command_publisher.publish(String(data='button'))
        self.get_logger().info('Publishing to Teensy: button')
        
        self.stage = 'SEARCH_BALL'
        self.ready = False
        self.dribble_sent = False

        # data from camera
        self.ball = 'no ball'
        self.ball_dir = 'forward'
        self.goal = 'no goal'
        self.goal_dir = 'right'

        self.in_dribble_mode = False
        self.just_shot = False

    def publish_stage(self):
        if not self.ready:
            return
        
        if self.ball_dir == 'dribble' and not self.just_shot:
            # if not self.in_dribble_mode:
            #     self.get_logger().info('Entering dribble mode')
            self.in_dribble_mode = True
        else:
            self.in_dribble_mode = False
            self.just_shot = False
        
        new_stage = 'SEARCH_BALL'

        if self.ball == 'ball':
            if self.ball_dir == 'forward':
                new_stage = 'APPROACH_BALL'

        if self.in_dribble_mode:
            new_stage = 'SEARCH_GOAL'

            if self.goal == 'goal':
                if self.goal_dir == 'forward':
                    new_stage = 'APPROACH_GOAL'

                elif self.goal_dir == 'shoot':
                    new_stage = 'SHOOT'
                    self.in_dribble_mode = False
                    self.just_shot = True
                    new_stage = 'SEARCH_BALL'
        
        old_stage = self.stage
        self.stage = new_stage
        
        # detect stage change
        if self.stage != old_stage:
            # entered goal-search mode
            if self.stage == 'SEARCH_GOAL':
                self.command_publisher.publish(String(data='dribble'))

            # left goal-search mode
            elif old_stage == 'SEARCH_GOAL' and self.stage != 'SEARCH_GOAL':
                self.command_publisher.publish(String(data='ndribble'))
            
        # publish stage
        stage = String()
        stage.data = self.stage
        self.stage_publisher.publish(stage)
        self.get_logger().info(f'Publishing to camera: {stage.data}')


    def publish_command(self):
        command = String()

        # if line seen, go back no matter what
        if self.ball == 'back':
            # print('BACKKKKKKK')
            command.data = 'back'
        
        elif self.stage in ['SEARCH_BALL', 'APPROACH_BALL']:
            command.data = self.ball_dir

        elif self.stage in ['SEARCH_GOAL', 'APPROACH_GOAL', 'SHOOT']:
            command.data = self.goal_dir

        self.command_publisher.publish(command)
        self.get_logger().info(f'Publishing to Teensy: {command.data}')
    

    def interpret_camera(self, msg):
        self.ready = True
        cam_data = msg.data
        #self.get_logger().info(f'Camera sees {cam_data}')

        if "|" in cam_data:
            cam_msg = cam_data.split("|")

            thing = cam_msg[0].strip()
            direction = cam_msg[1].strip()

            if thing == 'ball':
                self.ball = thing
                self.ball_dir = direction
            elif thing == 'no ball':
                self.ball = thing
                self.ball_dir = 'right'
            elif thing == 'goal':
                self.goal = thing
                self.goal_dir = direction
            elif thing == 'no goal':
                self.goal = thing
                self.goal_dir = 'right'
            elif thing == 'back':
                self.ball = thing

        self.publish_command()
        # command = String()

        # # if line seen, go back no matter what
        # if self.ball == 'back':
        #     print('BACKKKKKKK')
        #     command.data = 'back'
        
        # elif self.stage in ['SEARCH_BALL', 'APPROACH_BALL']:
        #     command.data = self.ball_dir

        # elif self.stage in ['SEARCH_GOAL', 'APPROACH_GOAL', 'SHOOT']:
        #     command.data = self.goal_dir

        # self.command_publisher.publish(command)
        # self.get_logger().info(f'Publishing to Teensy: {command.data}')
        



def main(args=None):
    rclpy.init(args=args)

    strategist = Strategist()

    rclpy.spin(strategist)

    strategist.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()       
