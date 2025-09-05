from typing import Dict, Any, List, Optional
import psycopg2

from MapViewer.app.config.settings import DATABASE_CONFIG
from MapManager.app.core.manager import handle_evacuations
from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import EVENT_TTL_SECONDS, MAP_MANAGER_QUEUE
from MapManager.app.core.event_state import EventState

from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler

logger = setup_logging("evacuation_consumer", "MapManager/logs/evacuationConsumer.log")

class EvacuationConsumer:
    def __init__(self, rabbitmq_handler: RabbitMQHandler, event_state: EventState):
        self.rabbit = rabbitmq_handler
        self.event_state = event_state
        logger.info("EvacuationConsumer inizializzato.")

    def start_consuming(self):
        self.rabbit.consume_messages(
            queue_name=MAP_MANAGER_QUEUE,
            callback=self.process_message
        )
        logger.info("Listening su MAP_MANAGER_QUEUE")

    def process_message(self, message: Dict[str, Any]):
        try:
            logger.info(f"Ricevuto payload: {message}")
            
            dangerous_nodes = message.get("dangerous_nodes") or []
            if not dangerous_nodes:
                logger.warning("Nessun nodo pericoloso nel messaggio.")
                return

            payload_event = (message.get("event") or "").strip() or None
            global_event = self.event_state.get()
            global_age = EventState.age_seconds()
            
            if payload_event:
                event_type = payload_event
                if payload_event != global_event:
                    EventState.set(payload_event)
                    logger.info(f"Aggiornato global event -> '{payload_event}' (source=payload)")
                # logger.info(f"Using event_type='{event_type}' for evacuation computation (source=payload)")
            else:
                # 2) Nessun evento nel payload -> fallback al globale solo se fresco
                if global_event and global_age <= EVENT_TTL_SECONDS:
                    event_type = global_event
                    logger.info(f"Using event_type='{event_type}' for evacuation computation (source=global, age={global_age:.1f}s)")
                else:
                    logger.warning("Né payload_event né global_event valido/fresco. Ignoro il batch.")
                    return
    
            floor_groups: Dict[int, List[int]] = {}
            for entry in dangerous_nodes:
                node_id = entry.get("node_id")
                if node_id is None:
                    continue
                for floor in self._get_node_floors(node_id) or []:
                    floor_groups.setdefault(floor, []).append(node_id)

            if not floor_groups:
                logger.warning("Nessun piano da processare.")
                return

            for floor, group in floor_groups.items():
                handle_evacuations(floor, group, event_type, rabbitmq_handler=self.rabbit)

        except Exception as e:
            logger.error(f"Errore processando MAP_MANAGER_QUEUE: {e}", exc_info=True)
            raise

    def _get_node_floors(self, node_id: int) -> Optional[List[int]]:
        try:
            conn = psycopg2.connect(**DATABASE_CONFIG)
            cur = conn.cursor()
            cur.execute("SELECT floor_level FROM nodes WHERE node_id = %s", (node_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row:
                return None
            floors = row[0]
            return floors if isinstance(floors, list) else [floors]
        except Exception as e:
            logger.error(f"Errore leggendo floor_level per node {node_id}: {e}")
            return None
