import time
import logging
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.handlers.alert_consumer import AlertConsumer
from NotificationCenter.app.handlers.alert_producer import AlertProducer
from NotificationCenter.app.config.settings import ALERT_QUEUE, MAP_MANAGER_QUEUE, USER_SIMULATOR_QUEUE, POSITION_REQUEST_QUEUE, EVACUATION_PATHS_QUEUE, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD

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

    # AlertProducer initialization
    # This is a mock producer for sending test messages to RabbitMQ
    # producer = AlertProducer(
    #     host=RABBITMQ_HOST,
    #     port=RABBITMQ_PORT,
    #     username=RABBITMQ_USERNAME,
    #     password=RABBITMQ_PASSWORD
    # )

    # Declare required queues
    for queue in [ALERT_QUEUE, MAP_MANAGER_QUEUE, 
                    USER_SIMULATOR_QUEUE, POSITION_REQUEST_QUEUE,
                    EVACUATION_PATHS_QUEUE]:
        rabbitmq_handler.declare_queue(queue)

    # Test alert messages to be sent
    # messaggio di allerta in json da Beatrice 
    # alert_messages = [
    #     {"id": "12345", "type": "Fire", "severity": "High", "area": "Zone A"},
    #     {"id": "67890", "type": "Flood", "severity": "Medium", "area": "Zone B"},
    #     {"id": "11111", "type": "Tornado", "severity": "Low", "area": "Zone C"}
    # ]

    # try:
    #     logger.info("Sending test alert messages...")
    #     for alert in alert_messages:
    #         producer.send_alert(alert)
    #         time.sleep(1)
    #     logger.info("All alert messages sent.")

    # except Exception as e:
    #     logger.error(f"Error in sending alerts: {e}")
    # finally:
    #     producer.close()

    consumer = AlertConsumer(rabbitmq_handler)
    logger.info("Starting alert consumer...")
    consumer.start_consuming()

    logger.info("Waiting for consumer to finish processing...")
    time.sleep(5)

if __name__ == "__main__":
    main()
