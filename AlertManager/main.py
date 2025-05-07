import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
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



def main():
    # 1. Create database connection
    conn = create_connection()

    if not conn:
        logger.error("Unable to connect to the database. The program will terminate.")
        return  # Exits the program if the connection fails

    try:
        # 2. Create tables in the database if they do not exist
        logger.info("Creating tables in the database if they do not exist...")
        create_tables()

        # 3. Define input and output folders
        input_dir = Path("AlertManager/data/input_cap")
        output_dir = Path("AlertManager/data/stored_cap")
        # Ensure output folder exists
        ensure_dir(output_dir)

        # 4. Select a random CAP file from the input folder
        logger.info("Selecting a random CAP file...")
        cap_content, original_name = get_random_cap(input_dir)
        logger.info(f"Selected CAP file: {original_name}")

        # 5. Convert the CAP XML content into a dictionary
        logger.info("Converting the CAP into a dictionary...")
        root = ET.fromstring(cap_content)  # Parse the XML content into an element
        cap_dict = xml_to_dict(root)  # Convert the XML element into a dictionary
        logger.info("CAP converted to dictionary.")

        # 10. Save historical version (XML + JSON)
        logger.info("Saving the alert in the historical folder (XML + JSON)...")
        save_cap_history(cap_content, output_dir)
        logger.info("Alert saved in the historical folder.")

        # 7. Load filter configuration
        logger.info("Loading the filter configuration...")
        base_dir = Path(__file__).resolve().parent
        config_path = base_dir / "config" / "filter_config.yaml"
        filter_config = load_filter_config(config_path)

        # 8. Apply filters to the CAP
        logger.info("Applying the filter...")
        if process_cap(cap_dict, filter_config):
            logger.info("Alert passed the filter. Sending to microservice...")

            # 9. Send the data to the microservice as a JSON message
            logger.info("Sending the data to the microservice...")
            producer = AlertProducer()
            producer.send_alert(cap_dict)
            producer.close()
            logger.info("Data sent to the microservice.")
            # 10. Attempt to save in the DB (even if it fails, sending is already done)
            try:
                logger.info("Inserting the alert into the database...")
                process_and_insert_alert(cap_dict, filter_config, conn)
            except Exception as db_err:
                logger.error(f"Error during database insertion: {db_err}")
        else:
            logger.warning("Alert did not pass the filter.")

    except Exception as e:
        logger.error(f"Error in the main process: {e}")
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")

if __name__ == "__main__":
    main()
