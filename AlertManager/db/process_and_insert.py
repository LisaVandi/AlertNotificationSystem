import json
import xml.etree.ElementTree as ET
import logging
import psycopg2
from psycopg2.extras import Json
from utils.filter import process_cap, load_filter_config
from data.cap_generator import xml_to_dict

# Configure the logger
logger = logging.getLogger(__name__)

def read_cap_from_file(file_path):
    """Reads the CAP XML file and converts it into a dictionary."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            cap_content = f.read()
        root = ET.fromstring(cap_content)
        cap_dict = xml_to_dict(root)
        return cap_dict
    except Exception as e:
        logger.error(f"❌ Error reading CAP file: {e}")
        return {}

def map_cap_to_db_fields(cap_alert):
    """Maps the CAP data to the database fields (only the necessary fields)."""
    return {
        "identifier": cap_alert.get("identifier"),
        "sender": cap_alert.get("sender"),
        "sent": cap_alert.get("sent"),
        "status": cap_alert.get("status"),
        "msgType": cap_alert.get("msgType"),
        "scope": cap_alert.get("scope")
    }

def get_relevant_alert_fields(alert_dict, filter_config):
    """
    Verifies the relevance of the main alert fields (such as identifier, sender, status, etc.)
    according to the filter configuration.
    """
    cap_filter = filter_config.get("cap_filter", {})

    for field in ['status', 'msgType', 'scope']:
        if field in alert_dict and alert_dict[field].strip().lower() not in [f.lower() for f in cap_filter.get(field, [])]:
            logger.debug(f"⚠️ Field '{field}' is not relevant according to the filter.")
            return False
    return True

def process_and_insert(cap_dict, conn, filter_config):
    """
    Processes and inserts the CAP data into the database.
    """
    logger.debug(f"Insertion process: cap_dict = {json.dumps(cap_dict, indent=2)}, filter_config = {json.dumps(filter_config, indent=2)}")

    try:
        cursor = conn.cursor()
        alert_id_str = cap_dict.get("identifier")

        if not alert_id_str:
            logger.error("⚠️ Alert ID missing in the dictionary.")
            return

        logger.info(f"🔧 Inserting data for the alert with ID: {alert_id_str}")

        # Check relevance of the 'alert' block
        if not get_relevant_alert_fields(cap_dict, filter_config):
            logger.warning("❌ Alert is not relevant at the 'alert' field level. Not processed.")
            return

        # Inserting into the alerts table
        cursor.execute('''
            INSERT INTO alerts (
                identifier, sender, sent, status, msgType, scope
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        ''', (
            alert_id_str,
            cap_dict.get("sender"),
            cap_dict.get("sent"),
            cap_dict.get("status"),
            cap_dict.get("msgType"),
            cap_dict.get("scope")
        ))

        alert_db_id = cursor.fetchone()[0]

        info = cap_dict.get("info")
        if isinstance(info, dict):
            info = [info]  # convert to list

        for alert_info in info:
            # Inserting into the info table
            cursor.execute('''
                INSERT INTO info (
                    alert_id, category, event, urgency, severity, certainty,
                    language, responseType, description, instruction
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            ''', (
                alert_db_id,
                alert_info.get("category"),
                alert_info.get("event"),
                alert_info.get("urgency"),
                alert_info.get("severity"),
                alert_info.get("certainty"),
                alert_info.get("language"),
                alert_info.get("responseType"),
                alert_info.get("description"),
                alert_info.get("instruction")
            ))

            # Inserting into the areas table
            areas = alert_info.get("areas", [])
            for area in areas:
                geom = area.get("geom")
                if geom:
                    try:
                        geom_json = json.dumps(geom)
                        cursor.execute('''
                            INSERT INTO areas (
                                alert_id, areaDesc, geometry_type, geom, altitude
                            ) VALUES (%s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s);
                        ''', (
                            alert_db_id,
                            area.get("areaDesc"),
                            geom.get("type"),  # e.g. "Polygon"
                            geom_json,
                            area.get("altitude")
                        ))
                    except Exception as e:
                        logger.error(f"⚠️ Error with the area geometry: {e}")
                        continue

        conn.commit()
        logger.info("✅ Alert successfully inserted into the database.")

    except Exception as e:
        logger.error(f"⚠️ Error during insertion into the database: {e}")
        conn.rollback()
    finally:
        cursor.close()


def process_and_insert_alert(cap_alert, filter_config, conn=None):
    # Log to verify what is being passed as a parameter
    logger.debug(f"Cap alert ID: {cap_alert.get('identifier')}, Sender: {cap_alert.get('sender')}")
    logger.debug(f"Filter keys: {list(filter_config.keys())}")


    # Ensure that filter_config is a dictionary and not a file
    if not isinstance(filter_config, dict):
        logger.error(f"❌ The filter is not a dictionary, but an object of type: {type(filter_config)}")
        return

    # Check that the connection is valid
    if conn is None:
        logger.error("❌ Database connection not provided.")
        return
    
    # Ensure that the insertion function is correctly called
    try:
        process_and_insert(cap_alert, conn, filter_config)  # Ensure cap_alert, conn, and filter_config are valid
        logger.info("✅ Alert successfully inserted into the database.")
    except Exception as e:
        logger.error(f"❌ Error during insertion into the database: {e}")
