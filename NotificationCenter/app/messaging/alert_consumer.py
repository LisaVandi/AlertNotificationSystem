import json
import logging
from typing import Dict, Any
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
from rabbitmq_handler import RabbitMQHandler

# Logger: configuration and initialization
logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

class AlertConsumer:
    def __init__(self, rabbitmq_handler: RabbitMQHandler):
        """
        Initializes the alert consumer with the RabbitMQ handler.
        Args:
            rabbitmq_handler (RabbitMQHandler): The RabbitMQHandler instance used to interact with RabbitMQ.
        """
        self.rabbitmq = rabbitmq_handler

    def process_alert(self, ch: BlockingChannel, method: Basic.Deliver, 
                     properties: BasicProperties, body: bytes):
        """
        Processes an incoming alert message from the messaging queue.
        Args:
            ch (BlockingChannel): The channel object used for communication with the messaging queue.
            method (Basic.Deliver): Delivery-related metadata for the message.
            properties (BasicProperties): Message properties, such as headers and delivery mode.
            body (bytes): The raw message body containing the alert data in JSON format.
        Raises:
            ValueError: If the alert data format is invalid.
        Behavior:
            - Parses the JSON-encoded alert data from the message body.
            - Logs the receipt of the alert with its ID.
            - Validates the alert data format using the `_validate_alert` method.
            - Handles the alert using the `_handle_alert` method if validation succeeds.
            - Acknowledges the message upon successful processing.
            - Logs success or failure of alert processing.
            - Sends a negative acknowledgment (NACK) if the alert is malformed or an error occurs.
                - If the error is a JSON decoding issue, the message is not requeued.
                - For other exceptions, the message is requeued for further processing.
        """
        try:
            alert_data = json.loads(body)
            logger.info(f"Alert ricevuto - ID: {alert_data.get('id')}")

            if not self._validate_alert(alert_data):
                raise ValueError("Formato alert non valido")

            self._handle_alert(alert_data)
            
            ch.basic_ack(delivery_tag=method.delivery_tag) 
            logger.info(f"Alert {alert_data['id']} processato con successo")

        except json.JSONDecodeError:
            logger.error("Alert malformato (JSON non valido)")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Errore durante l'elaborazione dell'alert: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    # CONTROLLA IN BASE A QUALI CAMPI CONFERMA BEATRICE 
    def _validate_alert(self, alert_data: Dict[str, Any]) -> bool:
        required_fields = {'id', 'type', 'severity', 'area'}
        return all(field in alert_data for field in required_fields)

    def _handle_alert(self, alert_data: Dict[str, Any]):
        """
        Handles the processing of an alert based on the provided alert data.
        Args:
            alert_data (Dict[str, Any]): A dictionary containing information about the alert.
                Expected keys include:
                    - 'id' (str): The unique identifier of the alert.
                    - 'type' (str): The type/category of the alert.
                    - 'severity' (str): The severity level of the alert.
        """
        
        logger.info(f"Elaborazione dell'allerta: {alert_data['id']} - Tipo: {alert_data['type']} - Severità: {alert_data['severity']}")
        # Aggiungere la logica per trattare l'allerta.

    def start_consuming(self, queue_name: str = 'alert_queue'):
        logger.info(f"In ascolto sulla coda {queue_name}...")
        self.rabbitmq.consume_messages(
            queue_name=queue_name,
            callback=self.process_alert,  
            prefetch_count=1  
        )


if __name__ == "__main__":
    rabbitmq_handler = RabbitMQHandler(host='localhost')  
    alert_consumer = AlertConsumer(rabbitmq_handler)
    alert_consumer.start_consuming(queue_name='alert_queue') # comunicare nome coda a beatrice
    
