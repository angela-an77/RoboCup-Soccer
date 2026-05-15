import rclpy
import serial
from rclpy.node import Node

from std_msgs.msg import String


class Teensy1Bridge(Node):
    
    def __init__(self):
        super().__init__('teensy1_bridge')

        self.sercon = serial.Serial('/dev/teensy1', 115200)
        self.subscription = self.create_subscription(
            String,
            'command',
            self.send_command,
            10) 

    
    def send_command(self, msg):
        command = msg.data
        self.get_logger().info(f'Sending to Teensy1: {command}')

        # Send command to Teensy 1
        self.sercon.write((command + '\n').encode())
    
    # # sending possession status
    # def send_serdata(self):
    #     if self.sercon.in_waiting:
    #         data = self.sercon.readline().decode()
    #         #self.buffer += data

    #         irbb_msg = String()
    #         irbb_msg.data = data

    #         self.pub.publish(irbb_msg)
    #         self.get_logger().info(f"Received: {irbb_msg.data}")



def main(args=None):
    rclpy.init(args=args)
    
    teensy1_bridge = Teensy1Bridge()

    rclpy.spin(teensy1_bridge)

    teensy1_bridge.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()


