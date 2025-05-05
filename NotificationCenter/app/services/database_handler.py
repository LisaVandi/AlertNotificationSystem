import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from NotificationCenter.app.config.settings import DATABASE_CONFIG
from NotificationCenter.app.config.logging import setup_logging

logger = setup_logging("database_handler", "NotificationCenter/logs/database.log")

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
        
    def close(self):
        self.cursor.close()
        self.conn.close()        
        logger.info("Database connection closed")