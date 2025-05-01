import json
from utils.filter import process_cap, load_filter_config
from data.cap_generator import xml_to_dict
import xml.etree.ElementTree as ET
import logging
import psycopg2
from psycopg2.extras import Json

# Configura il logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logger.info(f"json module loaded: {json is not None}")

def read_cap_from_file(file_path):
    """Legge il file XML CAP e lo converte in dizionario."""
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
    """Mappa i dati del CAP ai campi della tabella alerts (solo i campi necessari)."""
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
    Verifica la rilevanza dei campi principali dell'alert (come identifier, sender, status, etc.)
    rispetto alla configurazione del filtro.
    """
    cap_filter = filter_config.get("cap_filter", {}) 

    for field in ['status', 'msgType', 'scope']:
        if field in alert_dict and alert_dict[field].strip().lower() not in [f.lower() for f in cap_filter.get(field, [])]:
            logger.debug(f"⚠️ Campo '{field}' non rilevante per il filtro.")
            return False
    return True

def process_and_insert(cap_dict, conn, filter_config):
    """
    Funzione per elaborare e inserire i dati del CAP nel database.
    """
    logger.debug(f"Processo di inserimento: cap_dict = {json.dumps(cap_dict, indent=2)}, filter_config = {json.dumps(filter_config, indent=2)}")

    try:
        cursor = conn.cursor()
        alert_id_str = cap_dict.get("identifier")

        if not alert_id_str:
            logger.error("⚠️ Alert ID mancante nel dizionario.")
            return

        logger.info(f"🔧 Inserimento dei dati dell'alert con ID: {alert_id_str}")

        # Verifica la rilevanza del blocco 'alert'
        if not get_relevant_alert_fields(cap_dict, filter_config):
            logger.warning("❌ Alert non rilevante a livello di campo 'alert'. Non processato.")
            return

        # Inserimento nella tabella alerts
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
            info = [info]  # uniforma a lista

        for alert_info in info:
            # Inserimento nella tabella info
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

            # Inserimento nella tabella areas
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
                            geom.get("type"),  # es. "Polygon"
                            geom_json,
                            area.get("altitude")
                        ))
                    except Exception as e:
                        logger.error(f"⚠️ Errore nella geometria dell'area: {e}")
                        continue

        conn.commit()
        logger.info("✅ Alert inserito nel database.")

    except Exception as e:
        logger.error(f"⚠️ Errore durante l'inserimento nel database: {e}")
        conn.rollback()
    finally:
        cursor.close()


def process_and_insert_alert(cap_alert, filter_config, conn=None):
    # Log per verificare cosa arriva come parametro
    logger.debug(f"Cap alert: {json.dumps(cap_alert, indent=2)}")
    logger.debug(f"Filter config: {json.dumps(filter_config, indent=2)}")

    # Assicurati che filter_config sia un dizionario e non venga trattato come un file
    if not isinstance(filter_config, dict):
        logger.error("❌ Il filtro non è un dizionario, ma un oggetto di tipo: {}".format(type(filter_config)))
        return

    # Controlla che la connessione sia corretta
    if conn is None:
        logger.error("❌ Connessione al database non fornita.")
        return
    else:
        logger.debug("✅ Connessione al database valida.")
    
    # Verifica che venga chiamata correttamente la funzione di inserimento
    try:
        process_and_insert(cap_alert, conn, filter_config)  # Assicurati che cap_alert, conn e filter_config siano ok
        logger.info("✅ Alert inserito nel database.")
    except Exception as e:
        logger.error(f"❌ Errore nell'inserimento nel database: {e}")
