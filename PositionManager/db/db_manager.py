import psycopg2
from PositionManager.db.db_connection import create_connection
from PositionManager.utils.logger import logger

class DBManager:
    def __init__(self):
        self.conn = create_connection()

    def upsert_current_position(self, user_id, x, y, z, node_id, danger):
        try:
            with self.conn.cursor() as cursor:
                # Controlla se l'utente esiste già nella tabella current_position
                cursor.execute("""
                    SELECT 1 FROM current_position WHERE user_id = %s;
                """, (user_id,))
                result = cursor.fetchone()

                if result:  # Se l'utente esiste, esegui un update
                    cursor.execute("""
                        UPDATE current_position
                        SET x = %s, y = %s, z = %s, node_id = %s, danger = %s
                        WHERE user_id = %s;
                    """, (x, y, z, node_id, danger, user_id))
                else:  # Se l'utente non esiste, esegui un insert
                    cursor.execute("""
                        INSERT INTO current_position (user_id, x, y, z, node_id, danger)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (user_id, x, y, z, node_id, danger))

                self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to upsert current_position: {e}")


    def insert_historical_position(self, user_id, x, y, z, node_id, danger):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_historical_position (user_id, x, y, z, node_id, danger)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, node_id) DO NOTHING;
                """, (user_id, x, y, z, node_id, danger))
                self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to insert into user_historical_position: {e}")

    def get_dangerous_node_aggregates(self):
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

    def close(self):
        self.conn.close()
        self.conn.close()
