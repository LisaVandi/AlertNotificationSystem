"""
This script emulates the AlertManager by sending alert messages to the alert_queue in RabbitMQ.
It acts as a producer to test the AlertConsumer's ability to process alert messages.
"""
import logging
import time
from typing import Dict, Any

from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD
from NotificationCenter.app.config.logging import setup_logging

logger = setup_logging("alert_consumer","NotificationCenter/logs/alertConsumer.log")

class AlertProducer:
    def __init__(self, host: str, port: int, username: str, password: str):
        """
        Initializes the AlertProducer with a RabbitMQHandler.

        Args:
            host (str): The hostname or IP address of the RabbitMQ server.
            port (int): The port number of the RabbitMQ server.
            username (str): The username for RabbitMQ authentication.
            password (str): The password for RabbitMQ authentication.
        """
        self.rabbitmq = RabbitMQHandler(
            host=host,
            port=port,
            username=username,
            password=password
        )

    def send_alert(self, alert_message: Dict[str, Any], queue_name: str = 'alert_queue'):
        """
        Sends an alert message to the specified RabbitMQ queue.

        Args:
            alert_message (Dict[str, Any]): The alert message to send.
            queue_name (str): The name of the queue to send the message to. Defaults to 'alert_queue'.
        """
        try:
            self.rabbitmq.send_message(
                exchange='',
                routing_key=queue_name,
                message=alert_message,
                persistent=True
            )
            logger.info(f"Alert sent to {queue_name}: {alert_message}")
        except Exception as e:
            logger.error(f"Failed to send alert to {queue_name}: {e}")
            raise

    def close(self):
        """
        Closes the RabbitMQ connection.
        """
        self.rabbitmq.close()
        logger.info("AlertProducer closed")
