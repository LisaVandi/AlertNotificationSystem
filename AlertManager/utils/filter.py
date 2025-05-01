import yaml
import logging
import json

# Configura il logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

def load_filter_config(config_file="config/filter_config.yaml"):
    with open(config_file, "r") as file:
        return yaml.safe_load(file)

def process_cap(cap_dict, filter_config):
    f = filter_config["cap_filter"]
    info_blocks = cap_dict.get("info")

    if isinstance(info_blocks, dict):
        info_blocks = [info_blocks]  # Uniformiamo in lista

    if not info_blocks:
        logger.debug("❌ Nessun blocco 'info' trovato.")
        return False

    for info in info_blocks:
        logger.debug(f"🔍 Verifica blocco info: {json.dumps(info, indent=2)}")

        if "event" in f:
            cap_event = info.get("event")
            if isinstance(cap_event, list):
                if not any(event in f["event"] for event in cap_event):
                    continue  # questo blocco info non passa
            elif cap_event not in f["event"]:
                continue

        if "urgency" in f and info.get("urgency") not in f["urgency"]:
            continue

        if "severity" in f and info.get("severity") not in f["severity"]:
            continue

        if "certainty" in f and info.get("certainty") not in f["certainty"]:
            continue

        if "responseType" in f and info.get("responseType") not in f["responseType"]:
            continue

        # Check delle aree solo se definite
        area_descriptions = [
            area.get("areaDesc") for area in info.get("areas", []) if area.get("areaDesc")
        ]
        if "area" in f:
            if not any(area in f["area"] for area in area_descriptions):
                continue

        # Se è arrivato fino a qui, questo blocco info ha passato tutti i filtri
        logger.debug("✅ Blocco info passato. Alert valido.")
        return True

    logger.debug("❌ Nessun blocco info ha passato i filtri.")
    return False
