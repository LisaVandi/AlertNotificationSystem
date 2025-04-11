"""
Database Connection Utility

This script establishes a connection to a PostgreSQL database using psycopg2.
It uses Python's built-in logging module to log the connection status.

The script is compatible with databases that include the PostGIS extension,
though it does not perform any spatial operations directly.

Returns a connection object if successful, or logs an error and returns None if the connection fails.
"""

import psycopg2
import logging

# Configurazione del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurazione della connessione
DB_NAME = "alert_db"
DB_USER = "alert_user"
DB_PASSWORD = "Passworduser"
DB_HOST = "localhost"
DB_PORT = "5432"

# Funzione per creare la connessione al database
def create_connection():
    try:
        # Connessione al database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logger.info("✅ Connessione al database riuscita!")
        return conn
    except Exception as e:
        logger.error(f"❌ Errore di connessione: {e}")
        return None
