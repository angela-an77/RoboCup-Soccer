import rclpy
from rclpy.node import Node

from std_msgs.msg import String

# subscribes to data from all sensors and interprets it, publishes stage to all
class Strategist(Node):
    def __init__(self):
        super().__init__('strategist')
        
        self.stage = 'SEARCH_BALL'
        self.ready = False

        # data from camera
        self.ball = 'no ball'
        self.ball_dir = 'forward'
        self.goal = 'no goal'
        self.goal_dir = 'right'

        # data from IR BB (possession)
        self.pos = ''

        # pubs and subs
        self.stage_publisher = self.create_publisher(String, 'stage', 10)
        self.command_publisher = self.create_publisher(String, 'command', 10)

        self.cam_subscription = self.create_subscription(
            String,
            'cam_msg',
            self.interpret_camera,
            10)

        self.irbb_subscription = self.create_subscription(
            String,
            'irbb_msg',
            self.interpret_irbb,
            10
        )

        # run pubs and set stage constantly
        self.stage_timer = self.create_timer(0.05, self.publish_stage)
        self.command_timer = self.create_timer(0.5, self.publish_command)
    

    def publish_stage(self):
        if not self.ready:
            return
        else:
            if self.ball == 'ball' and self.ball_dir == 'forward':
                self.stage = 'APPROACH_BALL'
                # if self.pos == 'yes':
                #     self.stage = 'SEARCH_GOAL'
                #     if self.goal == 'goal':
                #         if self.goal_dir == 'forward':
                #             self.stage = 'APPROACH_GOAL'
                #         elif self.goal_dir == 'shoot':
                #             self.stage = 'SHOOT'
            else:
                self.stage = 'SEARCH_BALL'
            
            # publish stage
            stage = String()
            stage.data = self.stage
            self.stage_publisher.publish(stage)
            self.get_logger().info(f'Publishing to camera: {stage.data}')



    def publish_command(self):
        command = String()
        if self.stage in ['SEARCH_BALL', 'APPROACH_BALL']:
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
       
        command = String()
        if self.stage in ['SEARCH_BALL', 'APPROACH_BALL']:
            command.data = self.ball_dir

        elif self.stage in ['SEARCH_GOAL', 'APPROACH_GOAL', 'SHOOT']:
            command.data = self.goal_dir

        self.command_publisher.publish(command)
        self.get_logger().info(f'Publishing to Teensy: {command.data}')
    

    def interpret_irbb(self, msg):
        irbb_data = msg.data
        self.pos = irbb_data



def main(args=None):
    rclpy.init(args=args)

    strategist = Strategist()

    rclpy.spin(strategist)

    strategist.destroy_node()
    rclpy.shutdown()


if __name__ == 'main':
    main()       
