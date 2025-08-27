from typing import Dict, Any, List
import yaml

from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import MAP_ALERTS_QUEUE, ALERTS_CONFIG_PATH
from MapManager.app.services.db_writer import set_all_safe, set_nodes_safe, set_safe_by_floor
from MapManager.app.services.db_reader import (
    get_node_ids_by_type, get_node_ids_by_floor, get_all_node_ids, get_node_ids_in_zone
)
from MapManager.app.core.event_state import set_current_event, clear_current_event

logger = setup_logging("map_alert_consumer", "MapManager/logs/alertConsumer.log")

# Carico la configurazione delle emergenze una volta sola
try:
    with open(ALERTS_CONFIG_PATH, "r", encoding="utf-8") as f:
        EMERGENCY_CFG = yaml.safe_load(f) or {}
    logger.info(f"Loaded emergencies from {ALERTS_CONFIG_PATH}")
except Exception as e:
    logger.error(f"Cannot load {ALERTS_CONFIG_PATH}: {e}")
    EMERGENCY_CFG = {"emergencies": {}}

class AlertConsumer:
    """
    Consuma messaggi di allerta e aggiorna i flag 'safe' dei nodi secondo alerts.yaml.
    """
    def __init__(self, rabbitmq_handler):
        self.rabbit = rabbitmq_handler
        logger.info("AlertConsumer initialized")

    def start_consuming(self):
        self.rabbit.consume_messages(
            queue_name=MAP_ALERTS_QUEUE,
            callback=self._process_alert
        )

    def _process_alert(self, alert: Dict[str, Any]):
        try:
            msg_type = (alert or {}).get("msgType")
            if msg_type == "Cancel":
                logger.info("Received Cancel → set_all_safe(TRUE) & clear current event")
                set_all_safe(True)
                clear_current_event()
                return

            if msg_type not in ("Alert", "Update"):
                logger.warning(f"Ignoring message with msgType={msg_type}")
                return

            info = (alert.get("info") or [{}])[0]
            event_type = info.get("event", "")
            if not event_type:
                logger.warning("Alert without 'info.event'")
                return

            set_current_event(event_type)
            emergencies = EMERGENCY_CFG.get("emergencies", {})
            rule = emergencies.get(event_type)

            if not rule:
                logger.warning(f"Unknown event '{event_type}', applying default: all unsafe, { 'outdoor' } safe")
                set_all_safe(False)
                outdoors = get_node_ids_by_type("outdoor")
                set_nodes_safe(outdoors, True)
                return

            etype = rule.get("type")
            safe_node_type = rule.get("safe_node_type")

            # 1) reset coerente con il tipo di evento
            if etype == "all":
                # tutto unsafe, poi rendi safe la tipologia indicata
                set_all_safe(False)
                if safe_node_type:
                    ids = get_node_ids_by_type(safe_node_type)
                    set_nodes_safe(ids, True)
                logger.info(f"{event_type}: set all FALSE; safe {safe_node_type}=TRUE")
                return

            if etype == "floor":
                # per ciascun piano 'pericoloso' → safe=False
                danger_floors: List[int] = rule.get("danger_floors", [])
                for fl in danger_floors:
                    set_safe_by_floor(fl, False)
                # opzionale: rendi safe una tipologia (es. 'stairs')
                if safe_node_type:
                    ids = get_node_ids_by_type(safe_node_type)
                    set_nodes_safe(ids, True)
                logger.info(f"{event_type}: floors {danger_floors} FALSE; {safe_node_type}=TRUE")
                return

            if etype == "zone":
                # bounding box + range di piani
                dz = rule.get("danger_zone", {})
                x1, x2 = float(dz.get("x1", 0)), float(dz.get("x2", 0))
                y1, y2 = float(dz.get("y1", 0)), float(dz.get("y2", 0))
                z1, z2 = int(dz.get("z1", 0)), int(dz.get("z2", 0))
                
                ids = get_node_ids_in_zone(x1, x2, y1, y2, z1, z2)
                set_nodes_safe(ids, False)
                
                if safe_node_type:
                    safe_ids = get_node_ids_by_type(safe_node_type)
                    set_nodes_safe(safe_ids, True)
                logger.info(f"{event_type}: zone [{x1},{x2}]x[{y1},{y2}] z[{z1},{z2}] FALSE; {safe_node_type}=TRUE")
                return

            logger.warning(f"Unhandled rule type '{etype}' for event '{event_type}'")

        except Exception as e:
            logger.error(f"Error processing alert: {e}", exc_info=True)
            raise
