import os
import random
import json
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
import logging
from utils.logger import setup_logger
logger = setup_logger()


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
    """Function to get the text of a tag, if it exists, or a default value."""
    found_element = element.find(tag, ns)
    if found_element is not None:
        return found_element.text.strip() if found_element.text else default
    return default

def xml_to_dict(root):
    # Namespace for CAP (Common Alerting Protocol)
    ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}
    alert_data = {}

    # Required fields for the <alert> node
    alert_fields = ["identifier", "sender", "sent", "status", "msgType", "scope"]
    
    # Extract fields from the <alert> node
    for field in alert_fields:
        field_value = get_text_or_default(root, f'cap:{field}', ns)
        alert_data[field] = field_value
        
        # Log to verify the presence of required fields
        logger.info(f"<alert> field: {field} = {field_value}")
        if field_value is None or field_value == "":
            logger.warning(f"Required field missing or empty in <alert>: {field}")

    # Add optional fields for the <alert> node
    optional_alert_fields = ["source", "restriction", "address", "code", "note", "references", "incidents"]
    for field in optional_alert_fields:
        field_value = get_text_or_default(root, f'cap:{field}', ns)
        if field_value:
            alert_data[field] = field_value
            logger.info(f"Optional <alert> field: {field} = {field_value}")

    # Extract the <info> blocks, which may contain multiple pieces of information
    info_list = []
    for info_elem in root.findall('cap:info', ns):
        info_data = {}

        # Required fields for the <info> node
        info_fields = ["category", "event", "urgency", "severity", "certainty"]

        # Extract fields from the <info> node
        for field in info_fields:
            field_value = get_text_or_default(info_elem, f'cap:{field}', ns)
            info_data[field] = field_value
            
            # Log to verify required fields in the <info> node
            logger.info(f"<info> field: {field} = {field_value}")
            if field_value is None or field_value == "":
                logger.warning(f"Required field missing or empty in <info>: {field}")

        # Extract optional fields from the <info> node
        optional_fields = ["language", "responseType", "audience", "eventCode", "senderName", "headline", "description", "instruction", "contact", "web", "effective", "onset", "expires"]
        for field in optional_fields:
            field_value = get_text_or_default(info_elem, f'cap:{field}', ns)
            if field_value:
                info_data[field] = field_value
                logger.info(f"Optional <info> field: {field} = {field_value}")
        
        # Extract areas (optional)
        areas = []
        for area_elem in info_elem.findall('cap:area', ns):
            area_data = {}
            area_data["areaDesc"] = get_text_or_default(area_elem, 'cap:areaDesc', ns)

            # Extract optional fields for the <area> node
            optional_area_fields = ["polygon", "geocode", "altitude", "ceiling", "circle"]
            for field in optional_area_fields:
                field_value = get_text_or_default(area_elem, f'cap:{field}', ns)
                if field_value:
                    area_data[field] = field_value
                    logger.info(f"Optional <area> field: {field} = {field_value}")

            polygon_text = get_text_or_default(area_elem, 'cap:polygon', ns)
            if polygon_text:
                coords = [
                    [float(p.split(',')[1]), float(p.split(',')[0])]
                    for p in polygon_text.strip().split()
                ]
                if coords[0] != coords[-1]:
                    coords.append(coords[0])  # Close the polygon
                geom = {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
                area_data["geom"] = geom
            areas.append(area_data)

        # Add areas if present
        if areas:
            info_data["areas"] = areas
        
        # Add the <info> block data to the list
        info_list.append(info_data)

    # Add the <info> list to the alert data
    alert_data["info"] = info_list

    logger.info(f"Alert converted to dict: {json.dumps(alert_data, indent=2, ensure_ascii=False)}")
    
    return alert_data


def save_cap_history(cap_content: str, output_dir: Path):
    """Save the selected CAP as both XML and JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Save the original XML
    xml_path = output_dir / f"cap_{timestamp}.xml"
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(cap_content)
    
    # 2. Save a full JSON version (parsed from the XML)
    try:
        root = ET.fromstring(cap_content)
        json_data = xml_to_dict(root)
        
        json_path = output_dir / f"cap_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
    except ET.ParseError as e:
        print(f"JSON conversion error: {e}")
