import time
import logging
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.handlers.alert_consumer import AlertConsumer
from NotificationCenter.app.config.settings import ALERT_QUEUE, MAP_MANAGER_QUEUE, USER_SIMULATOR_QUEUE, POSITION_QUEUE, ALERTED_USERS_QUEUE, EVACUATION_PATHS_QUEUE, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD

# logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # RabbitMQHandler initialization
    rabbitmq_handler = RabbitMQHandler(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        username=RABBITMQ_USERNAME,
        password=RABBITMQ_PASSWORD
    )

    queues = [ALERT_QUEUE, MAP_MANAGER_QUEUE, 
                    USER_SIMULATOR_QUEUE, POSITION_QUEUE,
                    ALERTED_USERS_QUEUE, EVACUATION_PATHS_QUEUE]
    
    # Declare required queues
    for queue in queues:
        rabbitmq_handler.declare_queue(queue)

    consumer = AlertConsumer(rabbitmq_handler)
    logger.info("Starting alert consumer...")
    consumer.start_consuming()

    logger.info("Waiting for consumer to finish processing...")
    time.sleep(5)
    
    logger.info("Purging all queues before shutdown...")
    for queue in queues:
        try:
            rabbitmq_handler.purge_queue(queue)
        except Exception as e:
            logger.error(f"Failed to purge queue {queue}: {e}")

if __name__ == "__main__":
    main()
