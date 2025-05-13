import os
import sys

from NotificationCenter.app.handlers.alerted_users_consumer import AlertedUsersConsumer

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from MapManager.app.config.logging import setup_logging
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler  
from MapManager.app.config.settings import RABBITMQ_CONFIG
from MapManager.app.consumer.rabbitmq_consumer import EvacuationConsumer


logger = setup_logging("map_manager", "MapManager/logs/mapManager.log")

def main():
    try:
        rabbitmq_handler = RabbitMQHandler(
            host=RABBITMQ_CONFIG["host"],
            port=RABBITMQ_CONFIG["port"],
            username=RABBITMQ_CONFIG["username"],
            password=RABBITMQ_CONFIG["password"])
        logger.info("RabbitMQ consumer initialization for evacuations")
        
        # Consumer for ALERT_QUEUE
        alert_consumer = EvacuationConsumer(rabbitmq_handler)
        alert_consumer.start_consuming()
            
        # Consumer for ALERTED_USERS_QUEUE 
        alerted_users_consumer = AlertedUsersConsumer(rabbitmq_handler)
        alerted_users_consumer.start_consuming()
        
    except Exception as e:
        logger.error(f"Error during consumer initialization: {str(e)}")
        raise

if __name__ == "__main__":
    main()
