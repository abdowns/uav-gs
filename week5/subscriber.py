import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class Subscriber(Node):
    def __init__(self):
        super().__init__('subscriber')
        self.sub = self.create_subscription(
            String, 'topic', self.callback, 10
        )

    def callback(self, msg):
        self.get_logger().info(f'received: {msg.data}')

def main():
    rclpy.init()
    node = Subscriber()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()