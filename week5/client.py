import sys
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts

class Client(Node):
    def __init__(self):
        super().__init__('client')
        self.cli = self.create_client(AddTwoInts, 'add_two_ints')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('waiting for service')

    def send(self, a, b):
        request = AddTwoInts.Request()
        request.a = a
        request.b = b
        return self.cli.call_async(request)

def main():
    rclpy.init()
    node = Client()
    future = node.send(int(sys.argv[1]), int(sys.argv[2]))
    rclpy.spin_until_future_complete(node, future)
    print(f'Result: {future.result().sum}')
    node.destroy_node()
    rclpy.shutdown()