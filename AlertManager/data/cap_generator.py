import os
import random
import json
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

def ensure_dir(path: Path):
    """Create the folder if it doesn't exist"""
    path.mkdir(parents=True, exist_ok=True)

def get_random_cap(cap_folder: Path) -> tuple[str, str]:
    """Pick a random CAP file and return its content + filename"""
    cap_files = list(cap_folder.glob("*.xml"))
    if not cap_files:
        raise FileNotFoundError(f"No CAP files found in {cap_folder}")
    
    selected_file = random.choice(cap_files)
    with open(selected_file, "r", encoding="utf-8") as f:
        return f.read(), selected_file.name

def get_text_or_default(element, tag, ns, default=None):
    """Funzione per ottenere il testo di un tag, se esiste, o un valore di default."""
    found_element = element.find(tag, ns)
    if found_element is not None:
        return found_element.text.strip() if found_element.text else default
    return default

def xml_to_dict(root):
    # Namespace per il CAP (Common Alerting Protocol)
    ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
    alert_data = {}

    # Campi obbligatori per il nodo <alert>
    alert_fields = ["identifier", "sender", "sent", "status", "msgType", "scope"]
    
    # Estrazione dei campi dal nodo <alert>
    for field in alert_fields:
        field_value = get_text_or_default(root, f'cap:{field}', ns)
        alert_data[field] = field_value
        
        # Log per verificare la presenza dei campi obbligatori
        logger.info(f"Campo <alert>: {field} = {field_value}")
        if field_value is None or field_value == "":
            logger.warning(f"Campo obbligatorio mancante o vuoto in <alert>: {field}")

    # Aggiunta dei campi opzionali per il nodo <alert>
    optional_alert_fields = ["source", "restriction", "address", "code", "note", "references", "incidents"]
    for field in optional_alert_fields:
        field_value = get_text_or_default(root, f'cap:{field}', ns)
        if field_value:
            alert_data[field] = field_value
            logger.info(f"Campo opzionale <alert>: {field} = {field_value}")

    # Estrazione dei blocchi <info>, che possono contenere più informazioni
    info_list = []
    for info_elem in root.findall('cap:info', ns):
        info_data = {}

        # Campi obbligatori per il nodo <info>
        info_fields = ["category", "event", "urgency", "severity", "certainty"]

        # Estrazione dei campi dal nodo <info>
        for field in info_fields:
            field_value = get_text_or_default(info_elem, f'cap:{field}', ns)
            info_data[field] = field_value
            
            # Log per verificare i campi obbligatori nel nodo <info>
            logger.info(f"Campo <info>: {field} = {field_value}")
            if field_value is None or field_value == "":
                logger.warning(f"Campo obbligatorio mancante o vuoto in <info>: {field}")

        # Estrazione dei campi opzionali dal nodo <info> (facoltativi)
        optional_fields = ["language", "responseType", "audience", "eventCode", "senderName","headline", "description", "instruction", "contact", "web", "effective", "onset", "expires"]
        for field in optional_fields:
            field_value = get_text_or_default(info_elem, f'cap:{field}', ns)
            if field_value:
                info_data[field] = field_value
                logger.info(f"Campo opzionale <info>: {field} = {field_value}")
        

        # Estrazione delle aree (facoltative)
        areas = []
        for area_elem in info_elem.findall('cap:area', ns):
            area_data = {}
            area_data["areaDesc"] = get_text_or_default(area_elem, 'cap:areaDesc', ns)

            # Estrazione dei campi opzionali per il nodo <area>
            optional_area_fields = ["polygon", "geocode", "altitude", "ceiling", "circle"]
            for field in optional_area_fields:
                field_value = get_text_or_default(area_elem, f'cap:{field}', ns)
                if field_value:
                    area_data[field] = field_value
                    logger.info(f"Campo opzionale <area>: {field} = {field_value}")

            polygon_text = get_text_or_default(area_elem, 'cap:polygon', ns)
            if polygon_text:
                coords = [
                    [float(p.split(',')[1]), float(p.split(',')[0])]
                    for p in polygon_text.strip().split()
                ]
                if coords[0] != coords[-1]:
                    coords.append(coords[0])  # Chiusura del poligono
                geom = {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
                area_data["geom"] = geom
            areas.append(area_data)

        # Aggiungi le aree se presenti
        if areas:
            info_data["areas"] = areas
        
        # Aggiungi i dati del blocco <info> alla lista
        info_list.append(info_data)

    # Aggiungi la lista di <info> ai dati generali dell'alert
    alert_data["info"] = info_list

    logger.info(f"Alert converted to dict: {json.dumps(alert_data, indent=2, ensure_ascii=False)}")
    
    return alert_data


def save_cap_history(cap_content: str, output_dir: Path):
    """Salva il CAP selezionato sia come XML che come JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Salva l'XML originale
    xml_path = output_dir / f"cap_{timestamp}.xml"
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(cap_content)
    
    # 2. Salva una versione JSON completa (parsata dall'XML)
    try:
        root = ET.fromstring(cap_content)
        json_data = xml_to_dict(root)
        
        json_path = output_dir / f"cap_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
    except ET.ParseError as e:
        print(f"⚠️ Errore di conversione JSON: {e}")
