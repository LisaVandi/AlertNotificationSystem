"""
Reliable alert dispatcher to Map Manager.
"""
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import MAP_MANAGER_QUEUE
from NotificationCenter.app.config.logging import setup_logging, flush_logs

logger = setup_logging("alert_smister_to_map_manager", "NotificationCenter/logs/alertSmisterMapManager.log")

def send_alert_to_map_manager(rabbitmq_handler: RabbitMQHandler, message: dict) -> None:
    try:
        logger.debug(f"Sending alert to Map Manager: {message}")
        rabbitmq_handler.send_message(
            exchange="",
            routing_key=MAP_MANAGER_QUEUE,
            message=message
        )
        logger.info(f"Alert forwarded to Map Manager")
        flush_logs(logger)
    except Exception as e:
        logger.error(f"Failed to forward alert to Map Manager: {str(e)}")
        flush_logs(logger)
        raise