"""
Robust Alert Consumer with improved message handling.
"""
import json
from typing import Dict, Any
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import ALERT_QUEUE
from NotificationCenter.app.handlers.alert_smister_to_user_simulator import send_alert_to_user_simulator
from NotificationCenter.app.handlers.position_request import request_positions
from NotificationCenter.app.handlers.alert_smister_to_map_manager import send_alert_to_map_manager
from NotificationCenter.app.config.logging import setup_logging

logger = setup_logging("alert_consumer", "NotificationCenter/logs/alertConsumer.log")

class AlertConsumer:
    def __init__(self, rabbitmq_handler: RabbitMQHandler):
        self.rabbitmq = rabbitmq_handler
        logger.info("Alert Consumer initialized")

    def start_consuming(self):
        """Start consuming messages from the alert queue"""
        logger.info("Starting alert consumer")
        self.rabbitmq.consume_messages(
            queue_name=ALERT_QUEUE,
            callback=self.process_alert
        )

    def process_alert(self, alert_data: Dict[str, Any]):
        """Process incoming alert message"""
        try:
            logger.info(f"Received alert: {alert_data}")
            
            if not self._validate_alert(alert_data):
                raise ValueError("Invalid alert format")
            
            # Forward to Map Manager
            send_alert_to_map_manager(self.rabbitmq, alert_data)
            
            # Forward to User Simulator
            send_alert_to_user_simulator(self.rabbitmq, alert_data) 
            
            # Request positions
            request_positions(self.rabbitmq, alert_data.get("id"))
            
            logger.info("Alert processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing alert: {str(e)}")
            raise

    def _validate_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Validate alert structure"""
        required_fields = {"id", "type", "severity", "area"}
        return all(field in alert_data for field in required_fields)
