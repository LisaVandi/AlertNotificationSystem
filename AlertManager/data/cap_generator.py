"""
This script selects a random CAP (Common Alerting Protocol) XML file from the input directory,
parses its content, and stores a copy both as raw XML and as JSON in a history folder.
Useful for logging and transforming alert messages into more usable formats.
"""

import os
import random
import json
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

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

def xml_to_dict(element):
    """Recursively convert an XML element into a Python dictionary"""
    return {
        **element.attrib,
        "text": element.text.strip() if element.text else None,
        "children": [xml_to_dict(child) for child in element]
    }

def save_cap_history(cap_content: str, output_dir: Path):
    """Save the selected CAP both as raw XML and full JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Save the original XML
    xml_path = output_dir / f"cap_{timestamp}.xml"
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(cap_content)
    
    # 2. Save a full JSON version (parsed from XML)
    try:
        root = ET.fromstring(cap_content)
        json_data = xml_to_dict(root)
        
        json_path = output_dir / f"cap_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
    except ET.ParseError as e:
        print(f"⚠️ JSON conversion error: {e}")

def main():
    # Define input/output directories
    input_dir = Path("data/input_cap")
    output_dir = Path("data/stored_cap")
    ensure_dir(output_dir)
    
    try:
        # Step 1: Pick a random CAP
        cap_content, original_name = get_random_cap(input_dir)
        print(f"🔴 Selected CAP: {original_name}")
        
        # Step 2: Save it to history (XML + full JSON)
        save_cap_history(cap_content, output_dir)
        print("✅ Saved to stored_cap/ with all fields")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
