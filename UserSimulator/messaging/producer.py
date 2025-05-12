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

    def format_positions(self, positions):
        # Funzione per formattare le posizioni nel formato atteso dal PositionManager
        formatted_positions = []
        for time_slot_data in positions:
            time_slot = time_slot_data.get("time_slot")
            positions = time_slot_data.get("positions", [])
            formatted_positions.append({
                "time_slot": time_slot,
                "positions": [
                    {
                        "user_id": position.get("user_id"),
                        "node_id": position.get("node_id"),
                        "x": position.get("x"),
                        "y": position.get("y"),
                        "z": position.get("z")
                    }
                    for position in positions if all(k in position for k in ["user_id", "node_id", "x", "y", "z"])
                ]
            })
        return formatted_positions

    def send_positions(self, positions):
        # Formatta le posizioni prima di creare il messaggio
        formatted_positions = self.format_positions(positions)

        # Crea il messaggio con le posizioni formattate
        message = {
            "msgType": "Positions",
            "users_positions": formatted_positions
        }

        # Pubblica il messaggio sulla coda RabbitMQ
        self.handler.publish(self.queue_name, message)

        # Log del messaggio inviato
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_name,
            body=json.dumps(message)
        )
        logger.info(f"Sent positions to {self.queue_name}.")
