import signal
import sys
import time

from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.handlers.alert_consumer import AlertConsumer
from NotificationCenter.app.config.settings import ALERT_QUEUE, MAP_MANAGER_QUEUE, USER_SIMULATOR_QUEUE, POSITION_QUEUE, ALERTED_USERS_QUEUE, EVACUATION_PATHS_QUEUE, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD
from NotificationCenter.app.config.logging import setup_logging, flush_logs, close_logging

# logging configuration
logger = setup_logging("main", "NotificationCenter/logs/main.log")

def graceful_shutdown(logger):
    logger.info("Shutdown initiated, flushing and closing loggers...")
    flush_logs(logger)
    close_logging(logger)
    sys.exit(0)

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
    
    def signal_handler(sig, frame):
        graceful_shutdown(logger)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        consumer.start_consuming()
    except Exception as e:
        logger.error(f"Error starting consumer: {str(e)}")

    logger.info("Waiting for consumer to finish processing...")
    time.sleep(2)
    
    logger.info("Purging all queues before shutdown...")
    for queue in queues:
        try:
            rabbitmq_handler.purge_queue(queue)
        except Exception as e:
            logger.error(f"Failed to purge queue {queue}: {e}")
    graceful_shutdown(logger)

if __name__ == "__main__":
    main()
