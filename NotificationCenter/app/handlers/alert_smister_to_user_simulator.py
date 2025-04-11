"""
This module is responsible for sending messages to the User Simulator via RabbitMQ.
Notification Center receives the alert message from the Alert Manager and forwards it to the User Simulator.
"""
import logging
from services.rabbitmq_handler import RabbitMQHandler
from config.settings import USER_SIMULATOR_QUEUE

# Configure logging to write to a file
logging.basicConfig(
    filename="logs/notification.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def send_alert_to_user_simulator(rabbitmq_handler: RabbitMQHandler, message: dict) -> None:
    """
    Sends an alert message to the User Simulator via RabbitMQ.

    Args:
        rabbitmq_handler (RabbitMQHandler): The RabbitMQ handler instance.
        message (dict): The raw message received from the Alert Manager to forward.

    Raises:
        Exception: If the message cannot be sent to the User Simulator.
    """
    try:
        rabbitmq_handler.send_message(
            exchange="",
            routing_key=USER_SIMULATOR_QUEUE,
            message=message
        )
        logger.info(f"Alert sent to User Simulator: {message}")
    except Exception as e:
        logger.error(f"Error sending alert to User Simulator: {e}")
        raise