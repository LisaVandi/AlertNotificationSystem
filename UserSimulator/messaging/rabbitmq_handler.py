import pika
import json
import time
from typing import Callable, Dict
from utils.logger import logger

class RabbitMQHandler:
    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        attempts = 0
        while attempts < 3:
            try:
                self.connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
                self.channel = self.connection.channel()
                logger.info("RabbitMQ connected successfully.")
                return
            except Exception as e:
                attempts += 1
                logger.warning(f"Connection attempt {attempts} failed: {e}")
                time.sleep(2 ** attempts)
        raise ConnectionError("Could not connect to RabbitMQ after 3 attempts.")

    def declare_queue(self, queue_name: str, durable: bool = True):
        try:
            self.channel.queue_declare(queue=queue_name, durable=durable)
        except Exception as e:
            logger.error(f"Queue declaration failed: {e}")
            self._reconnect()
            raise

    def publish(self, queue_name: str, message: Dict):
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistente
                    content_type='application/json'
                )
            )
            logger.info(f"Message sent to {queue_name}")
        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            self._reconnect()
            raise

    def consume(self, queue_name: str, callback: Callable[[Dict], None]):
        def wrapped_callback(ch, method, properties, body):
            try:
                msg = json.loads(body)
                callback(msg)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Message handling error: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=queue_name, on_message_callback=wrapped_callback, auto_ack=False)
        logger.info(f"Consuming from {queue_name}")
        self.channel.start_consuming()

    def _reconnect(self):
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
        except Exception:
            pass
        self._connect()
