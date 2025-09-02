from typing import Dict, Any, List, Optional
import psycopg2

from MapViewer.app.config.settings import DATABASE_CONFIG
from MapManager.app.core.manager import handle_evacuations
from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import DEFAULT_EVENT_TYPE, MAP_MANAGER_QUEUE
from MapManager.app.core.event_state import EventState, set_current_event

from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler

logger = setup_logging("evacuation_consumer", "MapManager/logs/evacuationConsumer.log")

class EvacuationConsumer:
    """
    Consuma da MAP_MANAGER_QUEUE i nodi pericolosi aggregati (by PositionManager)
    e lancia il calcolo dei percorsi. NON modifica i flag 'safe' (che sono gestiti dall'alert).
    """
    def __init__(self, rabbitmq_handler: RabbitMQHandler):
        self.rabbit = rabbitmq_handler
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

            # Estraggo i nodi pericolosi
            dangerous_nodes = message.get("dangerous_nodes") or []
            if not dangerous_nodes:
                logger.warning("Nessun nodo pericoloso nel messaggio.")
                return

            # L’evento lo prendo dallo stato impostato dall’alert
            event_type = EventState.get()
            if not event_type:
                msg_event = message.get("event")
                if isinstance(msg_event, str) and msg_event.strip():
                    set_current_event(msg_event.strip())
                    event_type = msg_event.strip()
                    logger.info(f"Event impostato da payload → {event_type}")
                    
            if not event_type:
                logger.warning(f"Nessun evento nel sistema/payload.")

            # Raggruppo per piano usando i floor_level dal DB
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
            logger.error(f"Errore processando MAP_MANAGER_QUEUE: {e}")
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
