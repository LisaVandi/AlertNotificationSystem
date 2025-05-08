from messaging.rabbitmq_handler import RabbitMQHandler
from utils.logger import logger
import json
class UserSimulatorConsumer:
    def __init__(self, rabbitmq_url: str, queue_name: str, callback):
        self.handler = RabbitMQHandler(rabbitmq_url)
        self.queue_name = queue_name
        self.callback = callback
        self.handler.declare_queue(queue_name)

    def start_consuming(self):
        logger.info("Starting to consume messages...")
        self.handler.consume(self.queue_name, self.callback)

    def callback(self, ch, method, properties, body):
        logger.info(f"Received message: {body}")
        try:
            message = json.loads(body)
            logger.info(f"Processed message: {message}")
            # Passa il messaggio al controller per gestirlo
            self.callback.handle_message(message)
        except Exception as e:
            logger.error(f"Error processing message: {e}")