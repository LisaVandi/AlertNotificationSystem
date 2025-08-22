import signal, sys, time, threading

from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.handlers.alert_consumer import AlertConsumer
from NotificationCenter.app.handlers.alerted_users_consumer import AlertedUsersConsumer
from NotificationCenter.app.config.settings import (
    ALERT_QUEUE, MAP_MANAGER_QUEUE, USER_SIMULATOR_QUEUE, POSITION_QUEUE, 
    ALERTED_USERS_QUEUE, EVACUATION_PATHS_QUEUE, ACK_EVACUATION_QUEUE, 
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD
    )
from NotificationCenter.app.config.logging import setup_logging, flush_logs, close_logging

logger = setup_logging("main", "NotificationCenter/logs/main.log")

def graceful_shutdown():
    logger.info("Shutdown initiated, flushing and closing loggers...")
    flush_logs(logger)
    close_logging(logger)
    sys.exit(0)

def main():  
    handler_alerts = RabbitMQHandler(RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
    handler_paths  = RabbitMQHandler(RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD)

    queues = [ALERT_QUEUE, MAP_MANAGER_QUEUE, USER_SIMULATOR_QUEUE, POSITION_QUEUE,
              ALERTED_USERS_QUEUE, EVACUATION_PATHS_QUEUE, ACK_EVACUATION_QUEUE]
    
    # Declare required queues
    for queue in queues:
        handler_alerts.declare_queue(queue)

    alert_consumer = AlertConsumer(handler_alerts)
    alerted_users_consumer = AlertedUsersConsumer(handler_paths)
    logger.info("Starting consumers...")
    threads = [
        threading.Thread(target=alert_consumer.start_consuming, daemon=True),
        threading.Thread(target=alerted_users_consumer.start_consuming, daemon=True),
    ]
    for t in threads:
        t.start()
    
    def signal_handler(sig, frame):
        graceful_shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        while True:
            if not any(t.is_alive() for t in threads):
                logger.error("All consumer threads stopped; exiting...")
                break
            time.sleep(0.5)
    finally:
        try:
            admin = RabbitMQHandler(RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
            logger.info("Purging all queues before shutdown...")
            for q in queues:
                admin.purge_queue(q)
            admin.close()
        except Exception as e:
            logger.error(f"Failed during purge/shutdown: {e}")

    graceful_shutdown()

if __name__ == "__main__":
    main()
