import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class Publisher(Node):
    def __init__(self):
        super().__init__('publisher')
        self.pub = self.create_publisher(String, 'topic', 10)
        self.count = 0
        self.create_timer(0.5, self.publish)

    def publish(self):
        msg = String()
        msg.data = f'hello world: {self.count}'
        self.pub.publish(msg)
        self.count += 1

def main():
    rclpy.init()
    node = Publisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()