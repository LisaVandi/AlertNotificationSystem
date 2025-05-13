"""
EvacuationConsumer - gestore dei messaggi RabbitMQ per il MapManager
"""
from typing import Dict, Any

import psycopg2

from MapViewer.app.config.settings import DATABASE_CONFIG
from MapManager.app.core.manager import handle_evacuations
from MapManager.app.config.logging import setup_logging
from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler
from NotificationCenter.app.config.settings import MAP_MANAGER_QUEUE

logger = setup_logging("evacuation_consumer", "MapManager/logs/evacuationConsumer.log")

class EvacuationConsumer:
    def __init__(self, rabbitmq_handler: RabbitMQHandler):
        self.rabbitmq = rabbitmq_handler
        logger.info("Evacuation Consumer initialized")

    def start_consuming(self):
        """Avvia il consumo dalla coda MAP_MANAGER_QUEUE"""
        self.rabbitmq.consume_messages(
            queue_name=MAP_MANAGER_QUEUE,
            callback=self.process_message
        )
        logger.info(f"Starting evacuation consumer on Map Manager queue")

    def process_message(self, message: Dict[str, Any]):
        try:
            logger.info(f"Messaggio ricevuto: {message}")
            
            dangerous_nodes = message.get("dangerous_nodes", [])
            if not dangerous_nodes:
                logger.warning("Nessun nodo pericoloso trovato nel messaggio.")
                return

            nodes_in_alert = []

            for entry in dangerous_nodes:
                raw_node_id = entry.get("node_id")
                if not raw_node_id:
                    continue
                try:
                    numeric_id = int(raw_node_id.replace("N", ""))
                    nodes_in_alert.append(numeric_id)
                except ValueError:
                    logger.warning(f"node_id non valido: {raw_node_id}")
                    continue

            if not nodes_in_alert:
                logger.warning("Nessun node_id valido da processare.")
                return

            floor_level = self.get_floor_level_from_node(nodes_in_alert[0])

            # Richiama la logica di gestione delle evacuazioni
            handle_evacuations(floor_level, nodes_in_alert)

            logger.info("Evacuazione gestita con successo.")

        except Exception as e:
            logger.error(f"Errore nella gestione del messaggio: {str(e)}")
            raise
        
    def get_floor_level_from_node(self, node_id: int) -> int:
        try:
            conn = psycopg2.connect(**DATABASE_CONFIG)
            cur = conn.cursor()
            cur.execute("SELECT floor_level FROM nodes WHERE node_id = %s", (node_id,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Errore durante il recupero del floor_level per node_id={node_id}: {str(e)}")
            return 0
