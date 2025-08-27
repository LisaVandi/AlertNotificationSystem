"""
Database Connection Utility

This script establishes a connection to a PostgreSQL database using psycopg2.
It uses Python's built-in logging module to log the connection status.

The script is compatible with databases that include the PostGIS extension,
though it does not perform any spatial operations directly.

Returns a connection object if successful, or logs an error and returns None if the connection fails.
"""

import psycopg2
from MapViewer.app.config.settings import DATABASE_CONFIG
from MapViewer.app.config.logging import setup_logging

# Logging configuration
logger = setup_logging("MapViewer_dbconnection", "MapViewer/logs/dbWriter.log")

# Function to create a database connection
def create_connection():
    try:
        # Establish the database connection
        conn = psycopg2.connect(
            dbname=DATABASE_CONFIG["database"],
            user=DATABASE_CONFIG["user"],
            password=DATABASE_CONFIG["password"],
            host=DATABASE_CONFIG["host"],
            port=DATABASE_CONFIG["port"]
        )
        logger.info("Database connection successfull!")
        return conn
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return None
