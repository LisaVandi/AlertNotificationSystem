import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import time
import random

# Aggiungi la cartella principale (AlertNotificationSystem2) al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.cap_generator import get_random_cap, xml_to_dict, save_cap_history, ensure_dir
from utils.filter import process_cap, load_filter_config
from db.db_setup import create_tables
from db.process_and_insert import process_and_insert_alert  # Use process_and_insert
from db.db_connection import create_connection
from api.send_msg import AlertProducer
from utils.logger import setup_logger
logger = setup_logger()


def process_alert(conn, input_dir, output_dir, filter_config):
    """Processa un singolo alert, applica il filtro e lo invia se valido"""
    try:
        # Seleziona un file CAP casuale dalla cartella di input
        logger.info("Selecting a random CAP file...")
        cap_content, original_name = get_random_cap(input_dir)
        logger.info(f"Selected CAP file: {original_name}")

        # Converte il CAP in un dizionario
        logger.info("Converting the CAP into a dictionary...")
        root = ET.fromstring(cap_content)  # Parsing XML
        cap_dict = xml_to_dict(root)  # Converte l'elemento XML in un dizionario
        logger.info("CAP converted to dictionary.")

        # Salva la versione storica
        logger.info("Saving the alert in the historical folder (XML + JSON)...")
        save_cap_history(cap_content, output_dir)
        logger.info("Alert saved in the historical folder.")

        # Applica il filtro all'alert
        logger.info("Applying the filter...")
        if process_cap(cap_dict, filter_config):
            logger.info("Alert passed the filter. Sending to microservice...")

            # Invia il messaggio al microservizio
            producer = AlertProducer()
            producer.send_alert(cap_dict)
            producer.close()
            logger.info("Data sent to the microservice.")

            # Tenta di salvare l'alert nel DB (anche se fallisce, l'invio è già stato fatto)
            try:
                logger.info("Inserting the alert into the database...")
                process_and_insert_alert(cap_dict, filter_config, conn)
            except Exception as db_err:
                logger.error(f"Error during database insertion: {db_err}")
            return True  # L'alert è stato inviato e salvato con successo
        else:
            logger.warning("Alert did not pass the filter.")
            return False  # L'alert non è passato al filtro

    except Exception as e:
        logger.error(f"Error processing alert: {e}")
        return False  # Errore nel processo di gestione dell'alert


def main():
    # 1. Crea la connessione al database
    conn = create_connection()
    if not conn:
        logger.error("Unable to connect to the database. The program will terminate.")
        return

    try:
        # 2. Crea le tabelle nel database se non esistono
        logger.info("Creating tables in the database if they do not exist...")
        create_tables()

        # 3. Imposta le cartelle di input e output
        input_dir = Path("AlertManager/data/input_cap")
        output_dir = Path("AlertManager/data/stored_cap")
        ensure_dir(output_dir)  # Assicurati che la cartella di output esista

        # 4. Carica la configurazione del filtro
        logger.info("Loading the filter configuration...")
        base_dir = Path(__file__).resolve().parent
        config_path = base_dir / "config" / "filter_config.yaml"
        filter_config = load_filter_config(config_path)

        # 5. Ciclo per generare e processare gli alert finché uno non passa il filtro
        while True:
            logger.info("Attempting to process an alert...")
            if process_alert(conn, input_dir, output_dir, filter_config):
                logger.info("Alert processed successfully and sent to NotificationCenter.")
                break  # Interrompi il ciclo quando l'alert è stato inviato correttamente
            else:
                logger.info("Retrying with a new alert...")  # Se l'alert non passa, prova con uno nuovo
                time.sleep(1)  # Ritardo tra i tentativi

    except Exception as e:
        logger.error(f"Error in the main process: {e}")
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")


if __name__ == "__main__":
    main()
