# === core/messaging.py ===

import pika
import json
from config import settings
from config.logger import logger

def publish_message(queue_name, message):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Dichiarazione della coda come "durable" per evitare conflitti
    channel.queue_declare(queue=queue_name, durable=True)

    # Pubblicazione del messaggio
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=str(message),
        properties=pika.BasicProperties(
            delivery_mode=2  # Assicurati che i messaggi siano persistenti
        )
    )
    connection.close()