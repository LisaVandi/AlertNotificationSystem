import json
import pika
from typing import Callable
from utils.logger import logger

class UserSimulatorConsumer:
    def __init__(self, rabbitmq_url: str, queue_name: str, callback: Callable):
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.callback = callback

    def start_consuming(self):
        try:
            params = pika.URLParameters(self.rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.queue_declare(queue=self.queue_name, durable=True)
            logger.info(f"✅ Listening on queue: {self.queue_name}")

            def on_message(ch, method, properties, body):
                try:
                    message = json.loads(body.decode("utf-8"))
                    logger.info(f"📩 Received message: {message}")
                    self.callback(message)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"❌ Error processing message: {str(e)}")
                    ch.basic_nack(delivery_tag=method.delivery_tag)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=self.queue_name, on_message_callback=on_message)

            channel.start_consuming()
        except Exception as e:
            logger.error(f"❌ Error starting consumer: {str(e)}")
