"""
This module is responsible for sending messages to the Map Manager via RabbitMQ.
Notification Center receives the alert message from the Alert Manager and forwards it to the Map Manager.
"""
import logging
from services.rabbitmq_handler import RabbitMQHandler
from config.settings import MAP_MANAGER_QUEUE

# Configure logging to write to a file
logging.basicConfig(
    filename="logs/notification.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def send_alert_to_map_manager(rabbitmq_handler: RabbitMQHandler, message: dict) -> None:
    """
    Forward the received alert message to the Map Manager via RabbitMQ.

    Args:
        rabbitmq_handler (RabbitMQHandler): The RabbitMQ handler instance.
        message (dict): The raw message received from the Alert Manager to forward.

    Raises:
        Exception: If the message cannot be sent to the Map Manager.
    """
    try:
        rabbitmq_handler.send_message(
            exchange="",
            routing_key=MAP_MANAGER_QUEUE,
            message=message
        )
        logger.info(f"Alert sent to Map Manager: {message}")
    except Exception as e:
        logger.error(f"Error sending alert to Map Manager: {e}")
        raise