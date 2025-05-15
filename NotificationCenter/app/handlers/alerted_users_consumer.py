"""
Evacuation path consumer to forward messages to User Simulator.
"""
from typing import Dict, Any
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.handlers.alert_smister_to_user_simulator import send_alert_to_user_simulator, send_evacuation_path_to_user_simulator
from NotificationCenter.app.config.settings import ALERTED_USERS_QUEUE, USER_SIMULATOR_QUEUE
from NotificationCenter.app.config.logging import setup_logging

logger = setup_logging("alerted_users_consumer", "NotificationCenter/logs/alertedUsersConsumer.log")

class AlertedUsersConsumer:
    def __init__(self, rabbitmq_handler: RabbitMQHandler):
        self.rabbitmq = rabbitmq_handler
        logger.info("Alerted Users Consumer initialized")

    def start_consuming(self):
        """Start consuming messages from the alerted users queue"""
        logger.info("Starting alerted users consumer")
        self.rabbitmq.consume_messages(
            queue_name=ALERTED_USERS_QUEUE,
            callback=self.process_alerted_user
        )

    def process_alerted_user(self, alert_data: Dict[str, Any]):
        """Process incoming evacuation path message"""
        try:
            logger.info(f"Received evacuation data: {alert_data}")

            msg_type = alert_data.get("msgType")
            
            if msg_type == "Stop":
                logger.info("Received Stop message, sending to User Simulator")
                send_alert_to_user_simulator(self.rabbitmq, alert_data)
            
            elif "evacuation_path" in alert_data:
                alert_data["msgType"] = "Evacuation"
                logger.info(f"Sending evacuation path with msgType 'Evacuation' to User Simulator: {alert_data}")
                send_evacuation_path_to_user_simulator(self.rabbitmq, alert_data)

            logger.info("Evacuation path processed successfully")

        except Exception as e:
            logger.error(f"Error processing evacuation path: {str(e)}")
            raise
