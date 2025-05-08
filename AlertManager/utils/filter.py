import yaml
from utils.logger import setup_logger
logger = setup_logger()



def load_filter_config(config_file="config/filter_config.yaml"):
    with open(config_file, "r") as file:
        return yaml.safe_load(file)

def process_cap(cap_dict, filter_config):
    f = filter_config["cap_filter"]
    info_blocks = cap_dict.get("info")

    if isinstance(info_blocks, dict):
        info_blocks = [info_blocks]  # Normalize to list

    if not info_blocks:
        logger.debug("No 'info' block found.")
        return False

    for info in info_blocks:
        

        if "event" in f:
            cap_event = info.get("event")
            if isinstance(cap_event, list):
                if not any(event in f["event"] for event in cap_event):
                    continue  # this info block does not pass
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

        # Check areas only if defined
        area_descriptions = [
            area.get("areaDesc") for area in info.get("areas", []) if area.get("areaDesc")
        ]
        if "area" in f:
            if not any(area in f["area"] for area in area_descriptions):
                continue

        # If it reached here, this info block passed all the filters
        logger.debug("Info block passed. Valid alert.")
        return True

    logger.debug("No info block passed the filters.")
    return False
