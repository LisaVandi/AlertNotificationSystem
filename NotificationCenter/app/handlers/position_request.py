"""
Module for requesting user positions from the UserSimulator via RabbitMQ.
"""
import logging
from services.rabbitmq_handler import RabbitMQHandler
from config.settings import POSITION_REQUEST_QUEUE

# Configure logging to write to a file
logging.basicConfig(
    filename="logs/notification.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def request_positions(rabbitmq_handler: RabbitMQHandler, alert_id: str) -> None:
    """
    Sends a request for user positions to the Position Manager via RabbitMQ.

    Args:
        rabbitmq_handler (RabbitMQHandler): The RabbitMQ handler instance.
        alert_id (str): The ID of the alert for context.

    Raises:
        Exception: If the position request cannot be sent.
    """
    try:
        # Construct the position request message
        message = {
            "alert_id": alert_id,
            "request": "get_positions"
        }
        rabbitmq_handler.send_message(
            exchange="",
            routing_key=POSITION_REQUEST_QUEUE,
            message=message
        )
        logger.info(f"Position request sent to UserSimulator for alert {alert_id}: {message}")
    except Exception as e:
        logger.error(f"Error sending position request: {e}")
        raise