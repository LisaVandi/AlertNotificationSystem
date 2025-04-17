# This module will handle database connections and queries using psycopg2.
import logging
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import List, Tuple, Dict, Any, Callable
from MapViewer.app.config.settings import DATABASE_CONFIG

# Configure logging
logging.basicConfig(
    filename="MapViewer/logs/map_viewer.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

class DatabaseHandler:
    def __init__(self):
        """
        Initializes the database handler for PostgreSQL.
        """
        try:
            self.conn = psycopg2.connect(**DATABASE_CONFIG)
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # Required for LISTEN/NOTIFY
            self.cursor = self.conn.cursor()
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise       
        
    def fetch_current_positions(self) -> List[Tuple[int, int, int, int]]:
        try:
            self.cursor.execute("SELECT user_id, x, y, z FROM current_position")
            positions = self.cursor.fetchall()
            logger.info(f"Fetched {len(positions)} current positions")
            return positions
        except Exception as e:
            logger.error(f"Error fetching current positions: {e}")
            raise  
    
    def fetch_map_nodes(self) -> List[Dict[str, Any]]:
        try: 
            self.cursor.execute("SELECT node_id, x1, x2, y1, y2, z1, z2, floor_level, capacity, node_type FROM nodes")
            columns = [desc[0] for desc in self.cursor.description]
            nodes = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            logger.info(f"Fetched {len(nodes)} map nodes")
            return nodes
        except Exception as e:
            logger.error(f"Error fetching map nodes: {e}")
            raise

    def fetch_map_arcs(self) -> List[Dict[str, Any]]:
        try:
            self.cursor.execute("SELECT arc_id, flow, traversal_time, active, x1, x2, y1, y2, z1, z2, capacity, initial_node, final_node FROM arcs")
            columns = [desc[0] for desc in self.cursor.description]
            arcs = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            logger.info(f"Fetched {len(arcs)} map arcs")
            return arcs
        except Exception as e:
            logger.error(f"Error fetching map arcs: {e}")
            raise
        
    def update_user_position(self, user_id: str, x: float, y: float, z: float, danger_level: int = None):
        """
        Updates or inserts a user position in the posizione_attuale table and logs the update in storico_per_ogni_utente.

        Args:
            user_id (str): The ID of the user.
            x (float): The x-coordinate of the user's position.
            y (float): The y-coordinate of the user's position.
            z (float): The z-coordinate of the user's position.
            danger_level (int, optional): The danger level of the area.
        """
        try:
            # Update or insert the current position
            self.cursor.execute("""
                INSERT INTO current_position (user_id, x, y, z)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET x = %s, y = %s, z = %s
            """, (user_id, x, y, z, x, y, z))
            
            # Log the update in the historical table
            if danger_level is not None:
                self.cursor.execute("""
                    INSERT INTO user_historical_position (position_type, danger)
                    VALUES (%s, %s)
                """, ("update", danger_level))

            self.conn.commit()
            logger.info(f"Updated position for user {user_id}: ({x}, {y}, {z})")
        except Exception as e:
            logger.error(f"Error updating user position: {e}")
            self.conn.rollback()
            raise

    def get_user_positions(self) -> List[Tuple[str, float, float, float]]:
        """
        Retrieves all user positions from the posizione_attuale table.

        Returns:
            List[Tuple[str, float, float, float]]: List of (user_id, x, y, z) tuples.
        """
        try:
            self.cursor.execute("""
                SELECT user_id, x, y, z
                FROM current_position
            """)
            positions = self.cursor.fetchall()
            logger.info(f"Retrieved {len(positions)} user positions")
            return positions
        except Exception as e:
            logger.error(f"Error retrieving user positions: {e}")
            raise

    def get_map_nodes(self) -> List[Dict[str, Any]]:
        """
        Retrieves all map nodes from the nodes table.

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing node data.
        """
        try:
            self.cursor.execute("""
                SELECT node_id, x1, x2, y1, y2, z1, z2, floor, capacity, node_type
                FROM nodes
            """)
            columns = [desc[0] for desc in self.cursor.description]
            nodes = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            logger.info(f"Retrieved {len(nodes)} map nodes")
            return nodes
        except Exception as e:
            logger.error(f"Error retrieving map nodes: {e}")
            raise

    def get_map_edges(self) -> List[Dict[str, Any]]:
        """
        Retrieves all map edges from the arcs table.

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing edge data.
        """
        try:
            self.cursor.execute("""
                SELECT arc_id, flow, traversal_time, active, x1, x2, y1, y2, z1, z2, capacity, initial_node, final_node
                FROM arcs
            """)
            columns = [desc[0] for desc in self.cursor.description]
            edges = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            logger.info(f"Retrieved {len(edges)} map edges")
            return edges
        except Exception as e:
            logger.error(f"Error retrieving map edges: {e}")
            raise

    def listen_for_notifications(self, callback: Callable[[str], None]):
        """
        Listens for PostgreSQL notifications on the 'position_update' channel.

        Args:
            callback (Callable[[str], None]): The callback function to process notifications.
        """
        try:
            self.cursor.execute("LISTEN position_update;")
            logger.info("Listening for position update notifications...")
            while True:
                self.conn.poll()
                while self.conn.notifies:
                    notify = self.conn.notifies.pop(0)
                    logger.info(f"Received notification: {notify.payload}")
                    callback(notify.payload)
        except Exception as e:
            logger.error(f"Error listening for notifications: {e}")
            raise

    def listen_for_updates(self):
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor.execute("LISTEN position_update;")
        print("Listening for position updates...")

    def get_notification(self):
        if self.conn.notifies:
            return self.conn.notifies.pop(0)
        return None

    def close(self):
        self.cursor.close()
        self.conn.close()        
        logger.info("Database connection closed")