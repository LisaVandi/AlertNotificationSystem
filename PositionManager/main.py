import os 
import sys
# Aggiungi la cartella principale (AlertNotificationSystem2) al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PositionManager.rabbitmq.consumer import PositionManagerConsumer
import logging
from PositionManager.utils.logger import logger

def main():
    # Configura il logger
    logger.info("Starting PositionManager service...")

    try:
        # Avvio del consumer per consumare i messaggi dalla coda
        consumer = PositionManagerConsumer(config_file='PositionManager/config/config.yaml')
        consumer.start_consuming()  # Inizia a ricevere i messaggi dalla coda
    except Exception as e:
        logger.error(f"Failed to start PositionManager: {e}")

if __name__ == "__main__":
    main()
