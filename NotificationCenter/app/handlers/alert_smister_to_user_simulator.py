"""
Reliable alert dispatcher to User Simulator.
"""
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import USER_SIMULATOR_QUEUE
from NotificationCenter.app.config.logging import setup_logging

logger = setup_logging("alert_smister_to_user_simulator", "NotificationCenter/logs/alertSmisterUserSimulator.log")

def send_alert_to_user_simulator(rabbitmq_handler: RabbitMQHandler, message: dict) -> None:
    try:
        rabbitmq_handler.send_message(
            exchange="",
            routing_key=USER_SIMULATOR_QUEUE,
            message=message
        )
        logger.info("Alert forwarded to User Simulator")
    except Exception as e:
        logger.error(f"Failed to forward alert to User Simulator: {str(e)}")
        raise