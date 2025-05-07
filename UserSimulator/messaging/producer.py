import pika
import json
from utils.logger import logger
from messaging.rabbitmq_handler import RabbitMQHandler

class UserSimulatorProducer:
    def __init__(self, rabbitmq_url, queue_name):
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
        self.channel = self.connection.channel()
        self.handler = RabbitMQHandler(self.rabbitmq_url)  # Aggiungi questa riga per inizializzare il handler

    def send_positions(self, positions):
        # Crea il messaggio con le posizioni degli utenti
        message = {
            "msgType": "Positions",
            "users_positions": positions
        }

        # Log delle posizioni simulate per il debug
        logger.info(f"Generated positions: {json.dumps(positions, indent=2)}")

        # Pubblica il messaggio sulla coda RabbitMQ
        self.handler.publish(self.queue_name, message)

        # Log del messaggio inviato
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_name,
            body=json.dumps(message)
        )
        logger.info(f"Sent positions to {self.queue_name}.")
