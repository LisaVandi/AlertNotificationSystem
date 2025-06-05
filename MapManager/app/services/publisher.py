from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import ACK_EVACUATION_QUEUE

def publish_paths_ready(rabbit: RabbitMQHandler) -> None:
    """
    Publishes a message { "msg_type": "paths_ready" } to the ACK_EVACUATION_QUEUE.
    """
    try:
        payload = { "msg_type": "paths_ready" }
        rabbit.send_message(
            exchange="",
            routing_key=ACK_EVACUATION_QUEUE,
            message=payload,
            persistent=True
        )
    except Exception as e:
        print(f"Errore in publish_paths_ready: {e}")
        raise
