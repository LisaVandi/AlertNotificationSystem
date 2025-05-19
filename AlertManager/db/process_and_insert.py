import json
import xml.etree.ElementTree as ET
import psycopg2
from psycopg2.extras import Json
from utils.filter import process_cap, load_filter_config
from data.cap_generator import xml_to_dict
from utils.logger import setup_logger
logger = setup_logger()

# Reads a CAP XML file, converts it into a dictionary using xml_to_dict function
def read_cap_from_file(file_path):
    """Reads the CAP XML file and converts it into a dictionary."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            cap_content = f.read()  # Read the entire CAP file content
        root = ET.fromstring(cap_content)  # Parse the XML content into an ElementTree object
        cap_dict = xml_to_dict(root)  # Convert the XML data to a dictionary using xml_to_dict
        return cap_dict
    except Exception as e:
        logger.error(f"Error reading CAP file: {e}")  # Log an error if reading fails
        return {}

# Maps the relevant fields from the CAP alert to the database schema
def map_cap_to_db_fields(cap_alert):
    """Maps the CAP data to the database fields (only the necessary fields)."""
    return {
        "identifier": cap_alert.get("identifier"),  # Extract identifier
        "sender": cap_alert.get("sender"),  # Extract sender
        "sent": cap_alert.get("sent"),  # Extract sent date
        "status": cap_alert.get("status"),  # Extract status
        "msgType": cap_alert.get("msgType"),  # Extract message type
        "scope": cap_alert.get("scope")  # Extract scope
    }

# Verifies if the fields in the CAP alert match the criteria defined in the filter configuration
def get_relevant_alert_fields(alert_dict, filter_config):
    """
    Verifies the relevance of the main alert fields (such as identifier, sender, status, etc.)
    according to the filter configuration.
    """
    cap_filter = filter_config.get("cap_filter", {})  # Retrieve filter settings for CAP alerts

    # Check if the status, msgType, and scope fields are present and match the filter
    for field in ['status', 'msgType', 'scope']:
        if field in alert_dict and alert_dict[field].strip().lower() not in [f.lower() for f in cap_filter.get(field, [])]:
            logger.debug(f"Field '{field}' is not relevant according to the filter.")  # Log if the field is irrelevant
            return False  # Return False if the field does not meet filter criteria
    return True  # Return True if all the fields meet the filter criteria

# Main function to process and insert CAP data into the database
def process_and_insert(cap_dict, conn, filter_config):
    """
    Processes and inserts the CAP data into the database.
    """
    #logger.debug(f"Insertion process: cap_dict = {json.dumps(cap_dict, indent=2)}, filter_config = {json.dumps(filter_config, indent=2)}")

    try:
        cursor = conn.cursor()  # Create a cursor to interact with the database
        alert_id_str = cap_dict.get("identifier")  # Extract the alert identifier

        if not alert_id_str:
            logger.error("Alert ID missing in the dictionary.")  # Log error if no alert ID is found
            return

        logger.info(f"Inserting data for the alert with ID: {alert_id_str}")

        # Check the relevance of the alert fields (status, msgType, scope) based on the filter configuration
        if not get_relevant_alert_fields(cap_dict, filter_config):
            logger.warning("Alert is not relevant at the 'alert' field level. Not processed.")  # Log if alert is not relevant
            return

        # Insert the CAP alert data into the alerts table
        cursor.execute('''
            INSERT INTO alerts (
                identifier, sender, sent, status, msgType, scope
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        ''', (
            alert_id_str,  # Alert identifier
            cap_dict.get("sender"),  # Sender
            cap_dict.get("sent"),  # Sent time
            cap_dict.get("status"),  # Status
            cap_dict.get("msgType"),  # Message type
            cap_dict.get("scope")  # Scope
        ))

        alert_db_id = cursor.fetchone()[0]  # Retrieve the database ID of the inserted alert

        # Get the "info" data from the alert dictionary, which may contain multiple entries
        info = cap_dict.get("info")
        if isinstance(info, dict):
            info = [info]  # If "info" is a dictionary, convert it to a list

        # Iterate over each alert info and insert it into the database
        for alert_info in info:
            # Insert into the info table
            cursor.execute('''
                INSERT INTO info (
                    alert_id, category, event, urgency, severity, certainty,
                    language, responseType, description, instruction
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            ''', (
                alert_db_id,  # The database ID of the alert
                alert_info.get("category"),  # Category
                alert_info.get("event"),  # Event type
                alert_info.get("urgency"),  # Urgency level
                alert_info.get("severity"),  # Severity level
                alert_info.get("certainty"),  # Certainty level
                alert_info.get("language"),  # Language
                alert_info.get("responseType"),  # Response type
                alert_info.get("description"),  # Description
                alert_info.get("instruction")  # Instruction
            ))

            # Insert areas data into the areas table if present
            areas = alert_info.get("areas", [])
            for area in areas:
                geom = area.get("geom")  # Geometry data (polygon, circle, etc.)
                if geom:
                    try:
                        geom_json = json.dumps(geom)  # Convert geometry to JSON format
                        cursor.execute('''
                            INSERT INTO areas (
                                alert_id, areaDesc, geometry_type, geom, altitude
                            ) VALUES (%s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s);
                        ''', (
                            alert_db_id,  # The database ID of the alert
                            area.get("areaDesc"),  # Area description
                            geom.get("type"),  # Geometry type (e.g., Polygon)
                            geom_json,  # Geometry as JSON
                            area.get("altitude")  # Altitude if available
                        ))
                    except Exception as e:
                        logger.error(f"Error with the area geometry: {e}")  # Log any errors with geometry processing
                        continue

        conn.commit()  # Commit the transaction
        logger.info("Alert successfully inserted into the database.")

    except Exception as e:
        logger.error(f"Error during insertion into the database: {e}")  # Log errors during the insertion process
        conn.rollback()  # Rollback transaction if an error occurs
    finally:
        cursor.close()  # Close the cursor after the operation

# Function to process and insert a single CAP alert into the database
def process_and_insert_alert(cap_alert, filter_config, conn=None):
    # Log to verify what is being passed as a parameter
    logger.debug(f"Cap alert ID: {cap_alert.get('identifier')}, Sender: {cap_alert.get('sender')}")
    logger.debug(f"Filter keys: {list(filter_config.keys())}")

    # Ensure that filter_config is a dictionary and not a file
    if not isinstance(filter_config, dict):
        logger.error(f"The filter is not a dictionary, but an object of type: {type(filter_config)}")
        return

    # Check that the database connection is valid
    if conn is None:
        logger.error("Database connection not provided.")
        return
    
    # Ensure that the insertion function is correctly called
    try:
        process_and_insert(cap_alert, conn, filter_config)  # Process and insert the CAP alert
        logger.info("Alert successfully inserted into the database.")
    except Exception as e:
        logger.error(f"Error during insertion into the database: {e}")  # Log any errors during the process
