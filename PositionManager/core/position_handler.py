# === core/position_handler.py ===

from utils.db_utils import update_current_position, insert_historical_position, get_evacuation_path
from core.danger_detector import is_user_in_danger
from core.messaging import publish_message
from config import settings
from config.logger import logger

def handle_position(data):
    try:
        logger.debug(f"Messaggio ricevuto: {data}")

        node_to_users = {}  # Aggregazione per node_id

        if "users_positions" in data:
            for time_slot_data in data["users_positions"]:
                time_slot = time_slot_data.get("time_slot")
                for position in time_slot_data.get("positions", []):
                    user_id = position.get("user_id")
                    x = position.get("x")
                    y = position.get("y")
                    z = position.get("z")
                    node_id = position.get("node_id")

                    if not all([user_id, x is not None, y is not None, z is not None, node_id]):
                        logger.warning(f"Posizione malformata, scartata: {position}")
                        continue

                    user_position = {
                        "user_id": user_id,
                        "x": x,
                        "y": y,
                        "z": z,
                        "node_id": node_id
                    }

                    danger = is_user_in_danger(user_position)
                    user_position["danger"] = danger

                    update_current_position(user_position)
                    insert_historical_position(user_position)

                    if danger:
                        # Aggregazione per node_id
                        node_to_users.setdefault(node_id, []).append(user_id)

                        evacuation_path = get_evacuation_path(user_position["node_id"])
                        publish_message(settings.ALERTED_USERS_QUEUE, {
                            "user_id": user_id,
                            "evacuation_path": evacuation_path
                        })

                    logger.info(f"Gestita posizione utente {user_id}, danger={danger}")
        else:
            logger.warning(f"Messaggio malformato (manca 'users_positions'): {data}")

        # Invia messaggio aggregato al MapManager
        if node_to_users:
            aggregated_message = {
                "dangerous_nodes": [
                    {"node_id": node_id, "user_ids": user_ids}
                    for node_id, user_ids in node_to_users.items()
                ]
            }
            publish_message(settings.MAP_MANAGER_QUEUE, aggregated_message)

    except Exception:
        logger.exception("Errore nel processing della posizione")
