import psycopg2
from psycopg2 import sql
from PositionManager.utils.logger import logger


def create_connection():
    """Crea una connessione al database PostgreSQL"""
    try:
        conn = psycopg2.connect(
            dbname="map_position_db",  # Modifica con il nome del tuo DB
            user="postgres",      # Modifica con il tuo username DB
            password="postgres",  # Modifica con la tua password DB
            host="localhost",      # O l'indirizzo IP del server DB
            port="5432"            # Porta di default per PostgreSQL
        )
        logger.info("Connessione al database riuscita.")
        return conn
    except Exception as e:
        logger.error(f"Errore nella connessione al database: {e}")
        return None
