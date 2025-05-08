# === core/consumer.py ===

import pika
import json
from config import settings
from config.logger import logger
from core.position_handler import handle_position

_connection = pika.BlockingConnection(pika.ConnectionParameters(
    host=settings.RABBITMQ_HOST
))
_channel = _connection.channel()
_channel.queue_declare(queue=settings.POSITION_QUEUE, durable=True)

def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        handle_position(data)
    except Exception as e:
        logger.exception("Errore nel callback della coda")
        logger.warning(f"Messaggio scartato: {body}")

def start_consuming():
    logger.info("[PositionManager] In ascolto sulla coda POSITION_QUEUE...")
    _channel.basic_consume(queue=settings.POSITION_QUEUE, on_message_callback=callback, auto_ack=True)
    _channel.start_consuming()