import psycopg2
import logging

# Configurazione del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurazione della connessione
DB_NAME = "alert_db"  # Nome del tuo database
DB_USER = "alert_user"  # Nome utente del database
DB_PASSWORD = "Passworduser"  # Password del database
DB_HOST = "localhost"  # Indirizzo del server
DB_PORT = "5432"  # Porta predefinita di PostgreSQL

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

# Funzione di test per connettersi al database e verificare PostGIS
def test_postgis():
    conn = create_connection()
    if conn is None:
        print("❌ Connessione al database fallita.")
        return

    # Crea un cursore
    cursor = conn.cursor()

    # Verifica se PostGIS è abilitato
    try:
        cursor.execute("SELECT PostGIS_version();")
        postgis_version = cursor.fetchone()
        print(f"PostGIS è attivo! Versione: {postgis_version[0]}")
    except Exception as e:
        print(f"❌ Errore durante la verifica di PostGIS: {e}")
    
    # Chiudi la connessione
    cursor.close()
    conn.close()

if __name__ == "__main__":
    test_postgis()
