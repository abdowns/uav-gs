import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts

class Service(Node):
    def __init__(self):
        super().__init__('service')
        self.srv = self.create_service(
            AddTwoInts, 'add_two_ints', self.callback
        )

    def callback(self, request, response):
        response.sum = request.a + request.b
        return response

def main():
    rclpy.init()
    node = Service()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()