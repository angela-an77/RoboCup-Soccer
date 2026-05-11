import rclpy
import serial
from rclpy.node import Node

from std_msgs.msg import String


class Teensy2Bridge(Node):
    
    def __init__(self):
        super().__init__('teensy2_bridge')

        self.sercon = serial.Serial('/dev/teensy2', 115200)
        self.subscription = self.create_subscription(
            String,
            'command',
            self.send_command,
            10)

    
    def send_command(self, msg):
        command = msg.data
        self.get_logger().info(f'Sending to Teensy2: {command}')

        # Send command to Teensy 2
        self.sercon.write((command + '\n').encode())
    
    # Teensy will not send back any data (unless encoder gives useful info)
    # Just a reactor to command, determined by the stage, determined by the camera



def main(args=None):
    rclpy.init(args=args)
    
    teensy2_bridge = Teensy2Bridge()

    rclpy.spin(teensy2_bridge)

    teensy2_bridge.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()


