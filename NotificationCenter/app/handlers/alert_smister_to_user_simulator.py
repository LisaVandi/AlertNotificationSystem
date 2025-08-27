from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import USER_SIMULATOR_QUEUE, EVACUATION_PATHS_QUEUE, MAP_ALERTS_QUEUE
from NotificationCenter.app.config.logging import setup_logging

logger = setup_logging("alert_smister_to_user_simulator", "NotificationCenter/logs/alertSmisterUserSimulator.log")

def send_alert_to_user_simulator(rabbitmq_handler: RabbitMQHandler, message: dict) -> None:
    try:
        rabbitmq_handler.send_message(
            exchange="",
            routing_key=USER_SIMULATOR_QUEUE,
            message=message
        )
        logger.info(f"Forwarding alert to User Simulator: {message}")    
    except Exception as e:
        logger.error(f"Failed to forward alert to User Simulator: {str(e)}")
        raise

def send_evacuation_path_to_user_simulator(rabbitmq_handler: RabbitMQHandler, message: dict) -> None:
    try:
        rabbitmq_handler.send_message(
            exchange="",
            routing_key=EVACUATION_PATHS_QUEUE,
            message=message
        )
        logger.info(f"Evacuation path sent to User Simulator: {message}")
    except Exception as e:
        logger.error(f"Failed to send evacuation path to User Simulator: {str(e)}")
        raise
            
def send_alert_to_map_manager(rabbitmq_handler: RabbitMQHandler, message: dict) -> None:
    try:
        rabbitmq_handler.send_message(
            exchange="", 
            routing_key=MAP_ALERTS_QUEUE, 
            message=message)
        logger.info(f"Forwarding alert to MapManager: {message}")
    except Exception as e:
        logger.error(f"Failed to forward alert to MapManager: {str(e)}")
        raise            