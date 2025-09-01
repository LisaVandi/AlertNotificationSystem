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

            # Ignoring floor→node list format
            if (isinstance(alert_data, list) and alert_data
            and isinstance(alert_data[0], (list, tuple))
            and len(alert_data[0]) == 2 and isinstance(alert_data[0][1], list)):
                logger.warning("Received floor→node list (no evacuation_path). Ignoring.")
                return

            items: List[Dict[str, Any]] = alert_data if isinstance(alert_data, list) else [alert_data]

            batch: List[Dict[str, Any]] = []
            for item in items:
                if isinstance(item, dict) and item.get("msgType") == "Stop":
                    continue

                # --- Formato per-utente ---
                if isinstance(item, dict) and "user_id" in item and "evacuation_path" in item:
                    try:
                        uid = int(item["user_id"])
                        path_list = list(item["evacuation_path"])
                        if not path_list:
                            logger.warning("Empty evacuation_path for user_id=%s. Skipping.", uid)
                            continue
                        batch.append({"user_id": uid, "evacuation_path": path_list})
                    except Exception as e:
                        logger.warning("Invalid per-user item %s: %s", item, e)
                    continue

                # --- Formato per-nodo ---
                if isinstance(item, dict) and "node_id" in item and "evacuation_path" in item:
                    node_id = item.get("node_id")
                    evac_path = item.get("evacuation_path")
                    user_ids = item.get("user_ids") or []

                    # validazioni minime
                    try:
                        node_id = int(node_id)
                    except Exception:
                        logger.warning("Invalid node_id in item: %s", item)
                        continue

                    if not isinstance(evac_path, list) or not evac_path:
                        logger.warning("Empty/invalid evacuation_path for node_id=%s. Skipping.", node_id)
                        continue

                    # normalizza user_ids a int
                    try:
                        user_ids = [int(u) for u in user_ids]
                    except Exception:
                        logger.warning("Invalid user_ids in item for node_id=%s: %s", node_id, user_ids)
                        continue

                    if not user_ids:
                        logger.info("No users for node_id=%s; nothing to forward.", node_id)
                        continue

                    # espansione per-utente (path copiato per ciascun utente)
                    for uid in user_ids:
                        batch.append({"user_id": uid, "evacuation_path": list(evac_path)})
                    logger.info("Expanded node_id=%s to %d user messages", node_id, len(user_ids))
                    continue

                logger.warning("Skipping invalid item (unknown schema): %s", item)

            if batch:
                sent = 0
                for per_user in batch:
                    try:
                        send_evacuation_path_to_user_simulator(self.rabbitmq, per_user)
                        sent += 1
                        logger.info("Forwarded evacuation path for user_id=%s", per_user.get("user_id"))
                    except Exception as e:
                        logger.error("Failed to forward path for user_id=%s: %s",
                                     per_user.get("user_id"), str(e))
                logger.info("Forwarded %d per-user evacuation message(s) to User Simulator", sent)
            else:
                logger.info("No valid evacuation items to forward.")

        except Exception as e:
            logger.error("Error processing evacuation path: %s", str(e))