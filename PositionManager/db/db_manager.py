import psycopg2
import time
from PositionManager.db.db_connection import create_connection
from PositionManager.utils.logger import logger

class DBManager:
    """
    A class responsible for managing interactions with the PostgreSQL database.

    This class handles operations related to the `current_position` and `user_historical_position` tables, 
    including inserting, updating, and querying data.

    Attributes:
        conn (psycopg2.connection): The connection object to interact with the PostgreSQL database.
    """

    def __init__(self):
        """
        Initializes the DBManager instance by establishing a connection to the database.
        """
        self.conn = create_connection()
        self.node_safe_cache = {}
        self.cache_ttl = 5

    def upsert_current_position(self, user_id, x, y, z, node_id, danger):
        """
        Inserts or updates a user's position in the `current_position` table.

        If the user already exists in the `current_position` table, their position is updated.
        Otherwise, a new record is inserted.

        Args:
            user_id (int): The user's unique identifier.
            x (int): The user's current x-coordinate.
            y (int): The user's current y-coordinate.
            z (int): The user's current z-coordinate.
            node_id (int): The ID of the node where the user is located.
            danger (bool): A boolean indicating whether the user is in danger.
        """
        try:
            with self.conn.cursor() as cursor:
                # Check if the user already exists in the current_position table
                cursor.execute("""
                    SELECT 1 FROM current_position WHERE user_id = %s;
                """, (user_id,))
                result = cursor.fetchone()

                if result:  # If the user exists, update their position
                    cursor.execute("""
                        UPDATE current_position
                        SET x = %s, y = %s, z = %s, node_id = %s, danger = %s
                        WHERE user_id = %s;
                    """, (x, y, z, node_id, danger, user_id))
                else:  # If the user doesn't exist, insert a new record
                    cursor.execute("""
                        INSERT INTO current_position (user_id, x, y, z, node_id, danger)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (user_id, x, y, z, node_id, danger))

                self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to upsert current_position: {e}")

    def insert_historical_position(self, user_id, x, y, z, node_id, danger):
        """
        Inserts a user's position into the `user_historical_position` table.

        This method only inserts a new record if the combination of `user_id` and `node_id` does not already exist
        in the `user_historical_position` table.

        Args:
            user_id (int): The user's unique identifier.
            x (int): The user's historical x-coordinate.
            y (int): The user's historical y-coordinate.
            z (int): The user's historical z-coordinate.
            node_id (int): The ID of the node where the user was located.
            danger (bool): A boolean indicating whether the user was in danger.
        """
        try:
            with self.conn.cursor() as cursor:
                # Check if a record with the same user_id and node_id already exists in the historical table
                cursor.execute("""
                    SELECT 1 FROM user_historical_position WHERE user_id = %s AND node_id = %s;
                """, (user_id, node_id))
                result = cursor.fetchone()

                if result:  # If the record exists, do nothing
                    logger.info(f"User {user_id} at node {node_id} already exists in the historical table.")
                else:  # If the record doesn't exist, insert it
                    cursor.execute("""
                        INSERT INTO user_historical_position (user_id, x, y, z, node_id, danger)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (user_id, x, y, z, node_id, danger))
                    self.conn.commit()
                    logger.info(f"Inserted historical position for user {user_id} at node {node_id}.")
        except Exception as e:
            logger.error(f"Failed to insert into user_historical_position: {e}")

    def get_dangerous_node_aggregates(self):
        """
        Retrieves an aggregated list of dangerous nodes, where the danger status of users is TRUE.

        This method returns a list of dictionaries, each containing the `node_id` and a list of `user_ids`
        of users in danger at that node.

        Returns:
            list: A list of dictionaries with the node_id and user_ids of users in danger.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT node_id, array_agg(user_id)
                    FROM current_position
                    WHERE danger = TRUE
                    GROUP BY node_id;
                """)
                results = cursor.fetchall()
                return [{"node_id": node_id, "user_ids": user_ids} for node_id, user_ids in results]
        except Exception as e:
            logger.error(f"Failed to get dangerous node aggregates: {e}")
            return []

    def get_users_in_danger_with_paths(self):
        """
        Retrieves the list of users in danger, along with their corresponding evacuation paths.

        This method returns a list of tuples, where each tuple contains the `user_id` and a list of evacuation paths
        for the user based on their current node.

        Returns:
            list: A list of tuples, each containing the user_id and their evacuation path(s).
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT cp.user_id, n.evacuation_path
                    FROM current_position cp
                    JOIN nodes n ON cp.node_id = n.node_id
                    WHERE cp.danger = TRUE;
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get evacuation paths: {e}")
            return []
        
    def get_floor_level_by_node(self, node_id):
        """
        Retrieves the floor level of a node based on its node_id.

        Args:
            node_id (int): The ID of the node.

        Returns:
            int: The floor level of the node, or None if not found.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT floor_level
                    FROM nodes
                    WHERE node_id = %s;
                """, (node_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to retrieve floor_level for node {node_id}: {e}")
            return None
        
    def get_node_type(self, node_id):
        """
        Recupera il tipo di nodo (ad esempio 'stairs', 'outdoor', ecc.) dato il node_id.

        Args:
            node_id (int): L'ID del nodo.

        Returns:
            str or None: Il tipo di nodo o None se non trovato o errore.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT node_type
                    FROM nodes
                    WHERE node_id = %s;
                """, (node_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to retrieve node_type for node {node_id}: {e}")
            return None

    def is_everyone_safe(self):
        """
        Checks if all users in the current_position table have danger = FALSE.

        Returns:
            bool: True if no users are in danger, False otherwise.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM current_position WHERE danger = TRUE;
                """)
                result = cursor.fetchone()
                return result[0] == 0
        except Exception as e:
            logger.error(f"Failed to check danger status: {e}")
            return False  # Assume not safe if query fails

    def is_node_safe(self, node_id):
        import time
        now = time.time()
        if node_id in self.node_safe_cache:
            safe, ts = self.node_safe_cache[node_id]
            if now - ts < self.cache_ttl:
                return safe  # ritorna valore dalla cache

        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT safe
                    FROM nodes
                    WHERE node_id = %s;
                """, (node_id,))
                result = cursor.fetchone()
                safe = bool(result[0]) if result else False
                self.node_safe_cache[node_id] = (safe, now)  # aggiorna cache
                return safe
        except Exception as e:
            logger.error(f"Failed to retrieve safe flag for node {node_id}: {e}")
            return False
        
    def have_all_current_users_been_safe_once(self) -> bool:
        """
        Ritorna True se, per ogni utente attualmente presente in current_position,
        esiste almeno UNA riga nello storico con danger = FALSE.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM current_position cp
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM user_historical_position hp
                        WHERE hp.user_id = cp.user_id
                          AND hp.danger = FALSE
                    );
                """)
                missing = cursor.fetchone()[0]
                # True se NON esistono utenti privi di uno storico "safe"
                return missing == 0
        except Exception as e:
            logger.error(f"Failed to check historical safety condition: {e}")
            return False

    def is_stop_condition_satisfied(self) -> bool:
        """
        Lo Stop si può inviare SOLO se:
        1) nessun utente è in pericolo ORA (current_position)
        2) ogni utente attuale ha almeno uno storico con danger = FALSE
        """
        return self.is_everyone_safe() and self.have_all_current_users_been_safe_once()



    def get_aggregated_evacuation_data(self):
        """
        Ritorna una lista di dict con node_id, user_ids e evacuation_path.
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT cp.node_id, array_agg(cp.user_id), n.evacuation_path
                    FROM current_position cp
                    JOIN nodes n ON cp.node_id = n.node_id
                    WHERE cp.danger = TRUE
                    GROUP BY cp.node_id, n.evacuation_path;
                """)
                results = cursor.fetchall()
                # Trasformo in lista di dict per garantire formato coerente
                return [
                    {
                        "node_id": node_id,
                        "user_ids": user_ids,
                        "evacuation_path": evacuation_path if isinstance(evacuation_path, list) else [evacuation_path]
                    }
                    for node_id, user_ids, evacuation_path in results
                ]
        except Exception as e:
            logger.error(f"Failed to get aggregated evacuation data: {e}")
            return []



    def close(self):
        """
        Closes the connection to the PostgreSQL database.
        """
        self.conn.close()
