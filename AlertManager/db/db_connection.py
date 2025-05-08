"""
Database Connection Utility

This script establishes a connection to a PostgreSQL database using psycopg2.
It uses Python's built-in logging module to log the connection status.

The script is compatible with databases that include the PostGIS extension,
though it does not perform any spatial operations directly.

Returns a connection object if successful, or logs an error and returns None if the connection fails.
"""

import psycopg2
from utils.logger import setup_logger
logger = setup_logger()

# Database connection configuration
DB_NAME = "alert_db"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

# Function to create a database connection
def create_connection():
    try:
        # Establish the database connection
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logger.info("Database connection successful!")
        return conn
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return None
