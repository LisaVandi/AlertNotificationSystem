from typing import Dict, Any, List, Union
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.handlers.alert_smister_to_user_simulator import send_alert_to_user_simulator, send_evacuation_path_to_user_simulator
from NotificationCenter.app.config.settings import ALERTED_USERS_QUEUE
from NotificationCenter.app.config.logging import setup_logging

logger = setup_logging("alerted_users_consumer", "NotificationCenter/logs/alertedUsersConsumer.log")


class AlertedUsersConsumer:
    """
    Consumes messages from the alerted users queue and processes evacuation-related notifications.
    This consumer listens for messages indicating either an evacuation path or a stop command,
    and forwards them to the User Simulator via the appropriate handler functions.
    
    Methods:
        start_consuming():
            Begins consuming messages from the alerted users queue and processes each message
            using the `process_alerted_user` callback.
        process_alerted_user(alert_data: Dict[str, Any]):
            Processes an incoming message containing evacuation or stop instructions.
            Forwards the message to the User Simulator, handling both evacuation paths and stop commands.
    """
    
    def __init__(self, rabbitmq_handler: RabbitMQHandler):
        self.rabbitmq = rabbitmq_handler
        logger.info("Alerted Users Consumer initialized")

    def start_consuming(self):
        logger.info("Starting alerted users consumer")
        self.rabbitmq.consume_messages(
            queue_name=ALERTED_USERS_QUEUE,
            callback=self.process_alerted_user
        )
        
    def process_alerted_user(self, alert_data: Union[Dict[str, Any], List[Dict[str, Any]]]):
        try:
            logger.info(f"Received evacuation data: {alert_data}")

            # Forward Stop messages
            if isinstance(alert_data, dict) and alert_data.get("msgType") == "Stop":
                logger.info("Received Stop message, forwarding to User Simulator")
                send_alert_to_user_simulator(self.rabbitmq, alert_data)
                return
            
            items = alert_data if isinstance(alert_data, list) else [alert_data]
            batch = []
            for item in items:
                if item.get("msgType") == "Stop":
                    continue
                # formato per-utente
                if "user_id" in item and "evacuation_path" in item:
                    batch.append({"user_id": item["user_id"], "evacuation_path": item["evacuation_path"]})
                    continue
                # formato per-nodo
                node_id = item.get("node_id")
                evac_path = item.get("evacuation_path")
                user_ids = item.get("user_ids") or []
                if node_id is None or evac_path is None:
                    logger.warning("Skipping invalid item: %s", item)
                    continue
                for uid in user_ids:
                    batch.append({"user_id": uid, "evacuation_path": evac_path})

            if batch:
                send_evacuation_path_to_user_simulator(self.rabbitmq, batch)
                logger.info("Forwarded %d evacuation messages as a batch", len(batch))

        except Exception as e:
            logger.error("Error processing evacuation path: %s", str(e))
            raise