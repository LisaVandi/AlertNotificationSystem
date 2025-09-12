"""
Database Connection Utility

This script establishes a connection to a PostgreSQL database using psycopg2.
It uses Python's built-in logging module to log the connection status.

The script is compatible with databases that include the PostGIS extension,
though it does not perform any spatial operations directly.

Returns a connection object if successful, or logs an error and returns None if the connection fails.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from MapViewer.app.config.settings import DATABASE_CONFIG
from MapViewer.app.config.logging import setup_logging

# Logging configuration
logger = setup_logging("MapViewer_dbconnection", "MapViewer/logs/dbWriter.log")

def ensure_database_exists() -> None:
    """
    Ensures that the target database exists; if not, creates it.
    Requires the user to have CREATEDB privileges.
    """
    dbname = DATABASE_CONFIG["database"]
    try:
        # Connect to maintenance DB to manage databases
        admin_conn = psycopg2.connect(
            dbname="postgres",
            user=DATABASE_CONFIG["user"],
            password=DATABASE_CONFIG["password"],
            host=DATABASE_CONFIG["host"],
            port=DATABASE_CONFIG["port"],
        )
        admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        with admin_conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(f'CREATE DATABASE "{dbname}"')
                logger.info(f"Database '{dbname}' created.")

    except Exception as e:
        logger.error(f"Error ensuring database exists: {e}")
        raise
    finally:
        try:
            admin_conn.close()
        except Exception:
            pass

# Function to create a database connection
def create_connection():
    try:
        ensure_database_exists()
        
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
