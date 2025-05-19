import psycopg2
from psycopg2 import sql
from UserSimulator.utils.logger import logger


def create_connection():
    """
    Creates and returns a connection to the PostgreSQL database.
    
    Returns:
        conn (psycopg2.extensions.connection): A connection object if successful.
        None: If the connection fails.
    """
    try:
        conn = psycopg2.connect(
            dbname="map_position_db",   # Name of the target PostgreSQL database
            user="postgres",            # Database username
            password="postgres",        # Database password
            host="localhost",           # Host where the DB server is running (can be IP or domain)
            port="5432"                 # Default PostgreSQL port
        )
        logger.info("Database connection established successfully.")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")
        return None
