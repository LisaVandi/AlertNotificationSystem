import psycopg2
from psycopg2 import sql
from PositionManager.utils.logger import logger


def create_connection():
    """
    Creates a connection to the PostgreSQL database 'map_position_db'.
    
    This function establishes a connection to the database using the credentials
    provided in the connection parameters. If successful, it logs a connection success message.
    In case of an error (e.g., wrong credentials, DB unreachable), it logs an error and returns None.
    
    Returns:
        conn (psycopg2.connection): The connection object to interact with the PostgreSQL database.
        If the connection fails, None is returned.
    """
    try:
        # Attempt to connect to the PostgreSQL database
        conn = psycopg2.connect(
            dbname="map_position_db",  # Name of the database
            user="postgres",           # Database username
            password="postgres",       # Database password
            host="localhost",          # Host where the database is located (use IP for remote connections)
            port="5432"                # Default port for PostgreSQL
        )
        
        # If connection is successful, log the event
        logger.info("Database connection successful.")
        
        return conn
    
    except Exception as e:
        # If there is an error in connecting to the database, log the error message
        logger.error(f"Error connecting to the database: {e}")
        
        # Return None to indicate failure
        return None
