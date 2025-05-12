# === core/danger_detector.py ===
import os
import yaml
from config.logger import logger
from utils.db_utils import get_floor_from_node

# Percorso assoluto al file YAML
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "evacuation_config.yaml")
with open(CONFIG_PATH) as f:
    evacuation_config = yaml.safe_load(f)

current_alert = {"type": "Flood"}  # da aggiornare dinamicamente via ALERT_QUEUE

def is_user_in_danger(user_position):
    emergency = evacuation_config["emergencies"].get(current_alert["type"])
    if not emergency:
        return False

    if emergency["type"] == "all":
        return True
    if emergency["type"] == "floor":
        floor = get_floor_from_node(user_position["node_id"])
        return floor in emergency["danger_floors"]
    if emergency["type"] == "zone":
        zone = emergency["danger_zone"]
        return (zone['x1'] <= user_position['x'] <= zone['x2'] and
                zone['y1'] <= user_position['y'] <= zone['y2'] and
                zone['z1'] <= user_position['z'] <= zone['z2'])

    return False
