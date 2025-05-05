import json
import pika

class PositionProducer:
    def __init__(self, host="localhost", queue_name="user_position_queue"):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        self.channel = self.connection.channel()
        self.queue_name = queue_name
        self.channel.queue_declare(queue=self.queue_name, durable=True)

    def send_positions(self, positions):
        message = json.dumps({"positions": positions})
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_name,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2)
        )
