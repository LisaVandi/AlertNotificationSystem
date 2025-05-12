import os
import sys

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
        logger.info("Inizializzazione del consumer RabbitMQ per le evacuazioni")
        consumer = EvacuationConsumer(rabbitmq_handler)
        consumer.start_consuming()
    except Exception as e:
        logger.error(f"Errore durante l'inizializzazione del consumer: {str(e)}")
        raise

if __name__ == "__main__":
    main()
