# send_msg.py
import logging
from typing import Dict, Any

import sys
import os
# Aggiungi la cartella principale (AlertNotificationSystem2) al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD
from NotificationCenter.app.config.logging import setup_logging
from utils.logger import setup_logger

logger = setup_logger()

class AlertProducer:
    def __init__(self):
        self.rabbitmq = RabbitMQHandler(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            username=RABBITMQ_USERNAME,
            password=RABBITMQ_PASSWORD
        )

    def send_alert(self, alert_message: Dict[str, Any], queue_name: str = 'alert_queue'):
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
        self.rabbitmq.close()
        logger.info("AlertProducer closed.")
