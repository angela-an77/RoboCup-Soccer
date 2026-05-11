import rclpy
import serial
from rclpy.node import Node

from std_msgs.msg import String


class CameraBridge(Node):
    
    def __init__(self):
        super().__init__('camera_bridge')

        self.sercon = serial.Serial('/dev/openmvcam', 115200)
        self.subscription = self.create_subscription(
            String,
            'stage',
            self.send_stage,
            10)
        

        self.pub = self.create_publisher(String, 'cam_msg', 10)
        self.pub_timer = self.create_timer(0.05, self.send_serdata)

        self.last_stage = None

    def send_stage(self, msg):
        stage = msg.data

        if stage != self.last_stage:
            # Send command to camera
            self.sercon.write((stage + '\n').encode())
            self.get_logger().info(f'Sending to OpenMV: {stage}')
            self.last_stage = stage
    
    def send_serdata(self):
        latest = None
        while self.sercon.in_waiting:
            latest = self.sercon.readline().decode().strip()
            # print(data)

        if latest and "|" in latest:
            cam_msg = String()
            cam_msg.data = latest
            self.pub.publish(cam_msg)

            self.get_logger().info(f"Received: {cam_msg.data}")



def main(args=None):
    rclpy.init(args=args)
    
    camera_bridge = CameraBridge()

    rclpy.spin(camera_bridge)

    camera_bridge.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()


