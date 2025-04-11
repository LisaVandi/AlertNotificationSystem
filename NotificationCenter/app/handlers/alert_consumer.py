"""
This module defines the AlertConsumer class, which is responsible for consuming and processing alert messages from a RabbitMQ queue.
AlertManager-NotificationCenter integration is achieved through this consumer.
"""
import json
import logging
from typing import Dict, Any
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from services.rabbitmq_handler import RabbitMQHandler
from services.push_service import PushService
from NotificationCenter.app.handlers.alert_smister_to_map_manager import send_alert_to_map_manager
from NotificationCenter.app.handlers.alert_smister_to_user_simulator import send_alert_to_user_simulator
from handlers.position_request import request_positions

# Logger: configuration and initialization
logging.basicConfig(
    filename="logs/notification.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class AlertConsumer:
    def __init__(self, rabbitmq_handler: RabbitMQHandler):
        """
        Initializes the alert consumer with the RabbitMQ handler.
        
        Args:
            rabbitmq_handler (RabbitMQHandler): The RabbitMQHandler instance used to interact with RabbitMQ.
        """
        self.rabbitmq = rabbitmq_handler
        self.rabbitmq._channel.queue_declare(queue='alert_queue', durable=True)  
            
            
    def process_alert(self, message: Dict[str, Any]):
        """
        Processes an incoming alert message from the messaging queue.
        Extracts the alert ID and coordinates further actions.

        Args:
            message (Dict[str, Any]): The alert message in JSON format.
        """
        try:
            alert_id = message.get("id", None)  # Verify field name with Beatrice
            logger.info(f"Alert received - ID: {alert_id}")
            if not alert_id:
                logger.error("Alert ID not found in message")
                raise ValueError("Alert ID not found in message")

            # EVENTUAL SAVING OF ALERT ID IN A DATABASE OR FILE TO AVOID DUPLICATE PROCESSING

            if not self._validate_alert(message):
                raise ValueError("Invalid alert format")

            self._handle_alert(message)

            logger.info(f"Alert {alert_id} processed successfully")

        except Exception as e:
            logger.error(f"Error during alert processing: {str(e)}")
            raise


    def _validate_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Validates the format of the alert data.

        Args:
            alert_data (Dict[str, Any]): The alert data to validate.

        Returns:
            bool: True if the alert data is valid, False otherwise.
        """
        required_fields = {"id", "type", "severity", "area"}  # Confirm fields with Beatrice
        return all(field in alert_data for field in required_fields)
            
    def _handle_alert(self, message: Dict[str, Any]):
        """
        Handles the processing of an alert based on the provided alert data.
        Args:
            alert_data (Dict[str, Any]): A dictionary containing information about the alert.
                Expected keys include:
                    - 'id' (str): The unique identifier of the alert.
                    - 'type' (str): The type/category of the alert.
                    - 'severity' (str): The severity level of the alert.
        """
        
        logger.info(f"Elaborazione dell'allerta: {message['id']} - Tipo: {message['type']} - Severità: {message['severity']}")
        
        # Aggiungere la logica per trattare l'allerta.
        alert_id = message["id"]
        alert_message = f"Alert: {message['type']} - Severity: {message['severity']} in {message['area']}"
        logger.info(f"Processing alert: {alert_id} - Type: {message['type']} - Severity: {message['severity']}")

        # Step 1: Send push notifications to subscribed users
        
        # Step 2: Forward the alert to Map Manager
        send_alert_to_map_manager(self.rabbitmq, message)
        
        # Step 3: Forward the alert to User Simulator
        send_alert_to_user_simulator(self.rabbitmq, message)
        
        # Step 4: Request positions from User Simulator
        request_positions(self.rabbitmq, alert_id)        
        
    def start_consuming(self, queue_name: str = 'alert_queue'):
        """
        Starts consuming messages from the specified RabbitMQ queue.
        This method listens for incoming messages on the given queue and processes
        them using the `process_alert` callback function. It also sets the prefetch
        count to ensure that only one message is delivered to the consumer at a time.
        Args:
            queue_name (str): The name of the RabbitMQ queue to consume messages from.
                      Defaults to 'alert_queue'.
        """
        logger.info(f"Listening on queue {queue_name}...")
        self.rabbitmq.consume_messages(
            queue_name=queue_name,
            callback=self.process_alert,  
            prefetch_count=1  
        )

if __name__ == "__main__":
    # This block is for testing purposes; main.py will handle starting the consumer
    from config.rabbitmq_config import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD
    rabbitmq_handler = RabbitMQHandler(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        username=RABBITMQ_USERNAME,
        password=RABBITMQ_PASSWORD
    )
    alert_consumer = AlertConsumer(rabbitmq_handler)
    alert_consumer.start_consuming(queue_name="alert_queue")  # Confirm queue name with Beatrice