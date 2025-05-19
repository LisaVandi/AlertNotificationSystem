import logging
from typing import Dict, Any
import sys
import os

# Add the main folder (AlertNotificationSystem2) to sys.path for module imports.
# This ensures that the NotificationCenter and utils modules can be accessed from the current script.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import necessary classes and settings for RabbitMQ communication and logging configuration
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD
from NotificationCenter.app.config.logging import setup_logging
from utils.logger import setup_logger

# Initialize logger to handle logging of system activities and errors
logger = setup_logger()

class AlertProducer:
    """
    The AlertProducer class is responsible for sending alert messages to a specified RabbitMQ queue. 
    It establishes a connection with RabbitMQ, sends the alert messages, and provides logging for 
    the operations to track the success or failure of the alert sending process.
    """

    def __init__(self):
        """
        Initializes the AlertProducer instance by setting up the RabbitMQ connection handler.
        
        The RabbitMQHandler class is used to manage the communication between this application 
        and the RabbitMQ service using the credentials and connection settings defined in the config.
        """
        self.rabbitmq = RabbitMQHandler(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            username=RABBITMQ_USERNAME,
            password=RABBITMQ_PASSWORD
        )

    def send_alert(self, alert_message: Dict[str, Any], queue_name: str = 'alert_queue'):
        """
        Sends the provided alert message to the specified RabbitMQ queue.
        
        Args:
            alert_message (Dict[str, Any]): The message to be sent to the queue. It should be a dictionary 
                                            containing the relevant alert details.
            queue_name (str): The name of the RabbitMQ queue to which the alert message should be sent. 
                              Defaults to 'alert_queue'.
        
        Raises:
            Exception: If there is an error during the message sending process, an exception is raised 
                       after logging the error message.
        """
        try:
            # Sends the alert message to the specified RabbitMQ queue with 'persistent=True' 
            # to ensure that the message survives RabbitMQ restarts.
            self.rabbitmq.send_message(
                exchange='',
                routing_key=queue_name,
                message=alert_message,
                persistent=True
            )
            # Log the successful sending of the alert message
            logger.info(f"Alert sent to {queue_name}: {alert_message}")
        except Exception as e:
            # Log the failure of the alert sending process
            logger.error(f"Failed to send alert to {queue_name}: {e}")
            # Reraise the exception for further handling if necessary
            raise

    def close(self):
        """
        Closes the connection to RabbitMQ once the alert producer has completed its task.
        This is a cleanup operation to ensure the proper release of resources.
        """
        self.rabbitmq.close()
        # Log the closure of the AlertProducer
        logger.info("AlertProducer closed.")
