"""
Reliable position request handler.
"""
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import POSITION_REQUEST_QUEUE
from NotificationCenter.app.config.logging import setup_logging

logger = setup_logging("position_request", "NotificationCenter/logs/positionRequest.log")

def request_positions(rabbitmq_handler: RabbitMQHandler, alert_id: str) -> None:
    try:
        message = {
            "alert_id": alert_id,
            "request": "get_positions"
        }
        rabbitmq_handler.send_message(
            exchange="",
            routing_key=POSITION_REQUEST_QUEUE,
            message=message
        )
        logger.info(f"Position request sent for alert {alert_id}")
    except Exception as e:
        logger.error(f"Failed to send position request: {str(e)}")
        raise