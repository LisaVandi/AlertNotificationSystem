"""
Entry point for the Notification Center microservice.
Initializes and starts the consumers for alerts and evacuation paths.
"""
import asyncio
import logging
from handlers.alert_consumer import AlertConsumer
from handlers.path_handler import PathHandler
from services.rabbitmq_handler import RabbitMQHandler
from config.settings import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USERNAME,
    RABBITMQ_PASSWORD,
    ALERT_QUEUE,
    MAP_MANAGER_QUEUE,
    USER_SIMULATOR_QUEUE,
    POSITION_REQUEST_QUEUE,
    EVACUATION_PATHS_QUEUE,
)

def setup_logging() -> None:
    """
    Configures logging to write to a file with a consistent format.
    """
    logging.basicConfig(
        filename="logs/notification.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging configured for Notification Center")

async def main() -> None:
    """
    Main function to initialize and start the Notification Center microservice.
    """
    # Step 1: Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Notification Center microservice")

    # Step 2: Initialize RabbitMQHandler
    rabbitmq_handler = RabbitMQHandler(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        username=RABBITMQ_USERNAME,
        password=RABBITMQ_PASSWORD
    )

    # Step 3: Declare all necessary queues
    try:
        rabbitmq_handler.declare_queue(ALERT_QUEUE, durable=True)
        rabbitmq_handler.declare_queue(MAP_MANAGER_QUEUE, durable=True)
        rabbitmq_handler.declare_queue(USER_SIMULATOR_QUEUE, durable=True)
        rabbitmq_handler.declare_queue(POSITION_REQUEST_QUEUE, durable=True)
        rabbitmq_handler.declare_queue(EVACUATION_PATHS_QUEUE, durable=True)
        logger.info("All RabbitMQ queues declared successfully")
    except Exception as e:
        logger.error(f"Error declaring queues: {e}")
        raise

    # Step 4: Initialize consumers
    alert_consumer = AlertConsumer(rabbitmq_handler)
    path_handler = PathHandler()

    # Step 5: Start consumers in parallel
    try:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, alert_consumer.start_consuming),
            loop.run_in_executor(None, path_handler.start_consuming),
        ]
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutting down Notification Center")
        rabbitmq_handler.close()
    except Exception as e:
        logger.error(f"Error running consumers: {e}")
        rabbitmq_handler.close()
        raise

if __name__ == "__main__":
    asyncio.run(main())