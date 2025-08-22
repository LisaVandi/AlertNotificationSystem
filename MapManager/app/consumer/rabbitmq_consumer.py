from typing import Dict, Any, List, Optional

import psycopg2

from MapViewer.app.config.settings import DATABASE_CONFIG

from MapManager.app.core.manager import handle_evacuations
from MapManager.app.config.logging import setup_logging
from MapManager.app.config.settings import MAP_MANAGER_QUEUE

from NotificationCenter.app.services.rabbitmq_handler import RabbitMQHandler

logger = setup_logging("evacuation_consumer", "MapManager/logs/evacuationConsumer.log")

class EvacuationConsumer:
    def __init__(self, rabbitmq_handler: RabbitMQHandler):
        self.rabbitmq = rabbitmq_handler
        logger.info("EvacuationConsumer initialized")

    def start_consuming(self):
        """Start consuming messages from the MAP_MANAGER_QUEUE"""
        logger.info("Started consuming on MAP_MANAGER_QUEUE")
        self.rabbitmq.consume_messages(
            queue_name=MAP_MANAGER_QUEUE,
            callback=self.process_message
        )

    def process_message(self, message: Dict[str, Any]):
        try:
            logger.info(f"Received message: {message}")
            
            dangerous_nodes = message.get("dangerous_nodes", [])
            if not dangerous_nodes:
                logger.warning("No dangerous nodes found in message.")
                return
            
            event_type = message.get("event") or "Earthquake" # VERIFICA !!!
            if event_type is None:
                logger.error("Missing event type in message")
                return
            nodes_in_alert = []
            # update 'safe' label in DB and for users
            conn = psycopg2.connect(**DATABASE_CONFIG)
            cur = conn.cursor()
            # reset all nodes to safe=true
            cur.execute("UPDATE nodes SET safe = TRUE;")
            # reset user danger flags for safety
            cur.execute("UPDATE current_position SET danger = FALSE;")

            for entry in dangerous_nodes:
                node_id = entry.get("node_id")
                if node_id is None:
                    continue
                try:
                    numeric_id = int(node_id)
                    # set safe=false for this node
                    cur.execute("UPDATE nodes SET safe = FALSE WHERE node_id = %s;", (numeric_id,))
                    nodes_in_alert.append(numeric_id)
                    # users in danger
                    for uid in (entry.get("user_ids") or entry.get("users") or []):
                        try:
                            cur.execute("UPDATE current_position SET danger = TRUE WHERE user_id = %s;", (int(uid),))
                        except:
                            logger.warning(f"Cannot mark danger for user {uid}")
                except ValueError:
                    logger.warning(f"Invalid node_id format: {node_id}")
                    continue
            conn.commit()
            cur.close() 
            conn.close()

            if not nodes_in_alert:
                logger.warning("No valid node IDs found to process.")
                return

            floor_groups: Dict[int, List[int]] = {}
            for nid in nodes_in_alert:
                levels = self.get_floor_level(nid)  # può essere lista (scale) o int
                if levels is None:
                    continue
                if not isinstance(levels, list):
                    levels = [levels]
                for f in levels:
                    floor_groups.setdefault(f, []).append(nid)

            if not floor_groups:
                logger.warning("No floors to process.")
                return

            for f, group in floor_groups.items():
                handle_evacuations(f, group, event_type, rabbitmq_handler=self.rabbitmq)
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise

    def get_floor_level(self, node_id: int) -> Optional[List[int]]:
        """Retrieve floor level from DB for a given node ID"""
        try:
            conn = psycopg2.connect(**DATABASE_CONFIG)
            cur = conn.cursor()
            cur.execute("SELECT floor_level FROM nodes WHERE node_id = %s", (node_id,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error retrieving floor_level for node {node_id}: {str(e)}")
            return None
        
    def get_connected_floors(self, base_floor: int) -> List[int]:
        try:
            conn = psycopg2.connect(**DATABASE_CONFIG)
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT unnest(floor_level) 
                FROM nodes 
                WHERE %s = ANY(floor_level) 
                AND node_type = 'stairs'
            """, (base_floor,))
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()
            conn.close()