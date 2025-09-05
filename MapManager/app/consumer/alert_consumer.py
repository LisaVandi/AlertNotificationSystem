from typing import Dict, Any, List
import yaml

from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import MAP_ALERTS_QUEUE, ALERTS_CONFIG_PATH
from MapManager.app.services.db_writer import set_all_safe, set_nodes_safe, set_safe_by_floor
from MapManager.app.services.db_reader import (
    get_node_ids_by_type, get_node_ids_in_zone, get_node_attributes
)
from MapManager.app.core.event_state import EventState

logger = setup_logging("map_alert_consumer", "MapManager/logs/alertConsumer.log")

try:
    with open(ALERTS_CONFIG_PATH, "r", encoding="utf-8") as f:
        EMERGENCY_CFG = yaml.safe_load(f) or {}
    logger.info(f"Loaded emergencies from {ALERTS_CONFIG_PATH}")
except Exception as e:
    logger.error(f"Cannot load {ALERTS_CONFIG_PATH}: {e}")
    EMERGENCY_CFG = {"emergencies": {}}

class AlertConsumer:
    def __init__(self, rabbitmq_handler, event_state: EventState):
        self.rabbit = rabbitmq_handler
        self.event_state = event_state
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
                self.event_state.clear()
                return

            if msg_type not in ("Alert", "Update"):
                logger.warning(f"Ignoring message with msgType={msg_type}")
                return

            info = (alert.get("info") or [{}])[0]
            event_type = info.get("event", "")
            if not event_type:
                logger.warning("Alert without 'info.event'")
                return

            self.event_state.set(event_type)
            logger.info(f"[ALERT] event='{event_type}' set as current")

            emergencies = EMERGENCY_CFG.get("emergencies", {})
            rule = emergencies.get(event_type)

            if not rule:
                logger.warning(f"Unknown event '{event_type}', applying default: all unsafe, 'outdoor' safe")
                set_all_safe(False)
                outdoors = get_node_ids_by_type("outdoor")
                set_nodes_safe(outdoors, True)
                return

            etype = rule.get("type")
            safe_node_type = rule.get("safe_node_type")
            logger.info(f"Processing {event_type} with type={etype}, safe_node_type={safe_node_type}")

            if etype == "all":
                set_all_safe(False)
                if safe_node_type:
                    ids = get_node_ids_by_type(safe_node_type)
                    set_nodes_safe(ids, True)
                logger.info(f"{event_type}: set all FALSE; safe {safe_node_type}=TRUE")

            elif etype == "floor":
                # danger_floors = [int(f) for f in (rule.get("danger_floors") or [])]
                # safe_node_type: str | None = rule.get("safe_node_type")
                
                # set_all_safe(True)
                
                # for fl in danger_floors:
                #     set_safe_by_floor(fl, False)
                    
                # if safe_node_type:
                #     type_ids = list(set(get_node_ids_by_type(safe_node_type) or []))
                #     attrs = get_node_attributes(type_ids) or {}
                #     def flist(v): return v if isinstance(v, list) else [v]
                #     keep_safe_ids = [
                #         nid for nid, a in attrs.items()
                #         if any(int(f) in danger_floors for f in flist(a.get("floor_level")) if f is not None)
                #     ]
                #     if keep_safe_ids:
                #         set_nodes_safe(keep_safe_ids, True)
                #     logger.info(f"{event_type}: ALL=True; floors{danger_floors}=False; "
                #                 f"{safe_node_type} on those floors=True"
                #     )
                # dentro il ramo: if etype == "floor":
                danger_floors: List[int] = [int(x) for x in (rule.get("danger_floors") or [])]
                safe_node_type: str | None = rule.get("safe_node_type")

                # 0) (facoltativo ma consigliato) porta tutto a safe=True come baseline
                set_all_safe(True)

                # 1) marca i piani pericolosi come safe=False
                for fl in danger_floors:
                    set_safe_by_floor(fl, False)

                # 2) se previsto un tipo "sicuro" (per Flood: 'stairs'),
                #    riportalo a safe=True SOLO sui piani pericolosi (qui: 0),
                #    e FALLI DOPO il punto 1), così non vengono sovrascritti.
                if safe_node_type:
                    # prendi tutte le stairs
                    all_safe_ids = get_node_ids_by_type(safe_node_type)
                    # filtra quelle presenti sui piani pericolosi (es. 0)
                    attrs = get_node_attributes(all_safe_ids)  # -> {node_id: {"floor_level": [...], ...}, ...}
                    def as_set(v): 
                        return set(v if isinstance(v, list) else ([v] if v is not None else []))
                    target_ids = [
                        nid for nid, d in attrs.items()
                        if as_set(d.get("floor_level")) & set(danger_floors)
                    ]
                    if target_ids:
                        set_nodes_safe(target_ids, True)

                logger.info(
                    f"{event_type}: floors {danger_floors} set FALSE; "
                    f"{safe_node_type}@{danger_floors} forced TRUE"
                )

                

            elif etype == "zone":
                dz = rule.get("danger_zone", {})
                x1, x2 = float(dz.get("x1", 0)), float(dz.get("x2", 0))
                y1, y2 = float(dz.get("y1", 0)), float(dz.get("y2", 0))
                z1, z2 = int(dz.get("z1", 0)), int(dz.get("z2", 0))

                set_all_safe(True)
                ids = get_node_ids_in_zone(x1, x2, y1, y2, z1, z2)
                set_nodes_safe(ids, False)

                if safe_node_type:
                    safe_ids = get_node_ids_by_type(safe_node_type)
                    set_nodes_safe(safe_ids, True)
                logger.info(f"{event_type}: zone [{x1},{x2}]x[{y1},{y2}] z[{z1},{z2}] set FALSE; {safe_node_type}=TRUE")

            else:
                logger.warning(f"Unhandled rule type '{etype}' for event '{event_type}'")

        except Exception as e:
            logger.error(f"Error processing alert: {e}", exc_info=True)
            raise
