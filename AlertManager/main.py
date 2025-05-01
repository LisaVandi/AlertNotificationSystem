import os
import xml.etree.ElementTree as ET
from pathlib import Path
from data.cap_generator import get_random_cap, xml_to_dict, save_cap_history, ensure_dir
from utils.filter import process_cap, load_filter_config
from db.db_setup import create_tables
from db.process_and_insert import process_and_insert_alert  # Usa process_and_insert
from db.db_connection import create_connection
from api.send_msg import send_json_to_microservice
import logging
import json

# Configurazione del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # 1. Creazione della connessione al database
    conn = create_connection()

    if not conn:
        logger.error("❌ Impossibile connettersi al database. Il programma terminerà.")
        return  # Esce dal programma se la connessione fallisce

    try:
        # 2. Creazione delle tabelle nel database, se non esistono
        logger.info("🔨 Creazione delle tabelle nel database, se non esistono...")
        create_tables()

        # 3. Definisci le cartelle di input e output
        input_dir = Path("AlertManager/data/input_cap")
        output_dir = Path("AlertManager/data/stored_cap")

        # Assicurati che la cartella di output esista
        logger.info("📂 Controllo creazione della cartella di output...")
        ensure_dir(output_dir)

        # 4. Seleziona un file CAP casuale dalla cartella di input
        logger.info("🔍 Selezionando un file CAP casuale...")
        cap_content, original_name = get_random_cap(input_dir)
        logger.info(f"🔴 Selezionato il file CAP: {original_name}")

        # 5. Converte il contenuto XML del CAP in un dizionario
        logger.info("🔧 Converto il CAP in dizionario...")
        root = ET.fromstring(cap_content)  # Parso il contenuto XML in un elemento
        cap_dict = xml_to_dict(root)  # Converto l'elemento XML in un dizionario
        logger.info("🔧 CAP convertito in dizionario.")

        # 10. Salva la versione storica (XML + JSON)
        logger.info("💾 Salvataggio dell'alert nella cartella storica (XML + JSON)...")
        save_cap_history(cap_content, output_dir)
        logger.info("✅ Alert salvato nella cartella storica.")

        # 7. Carica la configurazione del filtro
        logger.info("📜 Caricamento della configurazione del filtro...")
        base_dir = Path(__file__).resolve().parent
        config_path = base_dir / "config" / "filter_config.yaml"
        filter_config = load_filter_config(config_path)

        # 8. Applica i filtri sul CAP
        logger.info("🔍 Applicazione del filtro...")
        if process_cap(cap_dict, filter_config):
            logger.info("✅ Alert passato al filtro. Invio al microservizio...")

            # 9. Invia i dati al microservizio come messaggio JSON
            logger.info("📡 Invia i dati al microservizio...")
            send_json_to_microservice(cap_dict)  # Passiamo i dati inseriti al microservizio
            logger.info("✅ Dati inviati al microservizio.")

            # 10. Prova a salvare nel DB (anche se fallisce, l'invio è già fatto)
            try:
                logger.info("📥 Inserimento dell'alert nel database...")
                process_and_insert_alert(cap_dict, filter_config, conn)
            except Exception as db_err:
                logger.error(f"⚠️ Errore durante l'inserimento nel database: {db_err}")
        else:
            logger.warning("❌ Alert non passato al filtro.")

    except Exception as e:
        logger.error(f"❌ Errore nel processo principale: {e}")
    finally:
        if conn:
            conn.close()
            logger.info("🔒 Connessione al database chiusa.")

if __name__ == "__main__":
    main()
