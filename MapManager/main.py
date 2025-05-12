from NotificationCenter.app.config.logging import setup_logging
from NotificationCenter.app.handlers import RabbitMQHandler  
from MapManager.app.consumer.rabbitmq_consumer import EvacuationConsumer

logger = setup_logging("map_manager", "MapManager/logs/mapManager.log")

def main():
    try:
        rabbitmq_handler = RabbitMQHandler()
        logger.info("Inizializzazione del consumer RabbitMQ per le evacuazioni")
        consumer = EvacuationConsumer(rabbitmq_handler)
        consumer.start_consuming()
    except Exception as e:
        logger.error(f"Errore durante l'inizializzazione del consumer: {str(e)}")
        raise

if __name__ == "__main__":
    main()
