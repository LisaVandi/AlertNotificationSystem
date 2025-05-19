import yaml
from utils.logger import setup_logger
logger = setup_logger()

# Function to load the filter configuration from a YAML file
def load_filter_config(config_file="config/filter_config.yaml"):
    """Loads the filter configuration from a YAML file."""
    with open(config_file, "r") as file:
        return yaml.safe_load(file)  # Parse the YAML file into a Python dictionary

# Function to process a CAP alert dictionary based on the filter configuration
def process_cap(cap_dict, filter_config):
    f = filter_config["cap_filter"]  # Get the CAP filter section from the configuration
    info_blocks = cap_dict.get("info")  # Extract the 'info' blocks from the CAP alert

    if isinstance(info_blocks, dict):
        info_blocks = [info_blocks]  # Normalize the 'info' blocks to a list if it's a single dictionary

    if not info_blocks:
        logger.debug("No 'info' block found.")  # Log if no 'info' block is found
        return False  # Return False if no 'info' blocks are available

    # Loop through each 'info' block in the CAP alert
    for info in info_blocks:
        # Filter by 'event' if specified in the filter configuration
        if "event" in f:
            cap_event = info.get("event")  # Get the event from the current info block
            if isinstance(cap_event, list):
                # If 'event' is a list, check if any of the events match the filter
                if not any(event in f["event"] for event in cap_event):
                    continue  # Skip this info block if no event matches the filter
            elif cap_event not in f["event"]:
                continue  # Skip this info block if the event does not match the filter

        # Filter by 'urgency' if specified in the filter configuration
        if "urgency" in f and info.get("urgency") not in f["urgency"]:
            continue  # Skip this info block if urgency does not match the filter

        # Filter by 'severity' if specified in the filter configuration
        if "severity" in f and info.get("severity") not in f["severity"]:
            continue  # Skip this info block if severity does not match the filter

        # Filter by 'certainty' if specified in the filter configuration
        if "certainty" in f and info.get("certainty") not in f["certainty"]:
            continue  # Skip this info block if certainty does not match the filter

        # Filter by 'responseType' if specified in the filter configuration
        if "responseType" in f and info.get("responseType") not in f["responseType"]:
            continue  # Skip this info block if responseType does not match the filter

        # Check areas if 'area' filter is defined
        area_descriptions = [
            area.get("areaDesc") for area in info.get("areas", []) if area.get("areaDesc")
        ]
        if "area" in f:
            if not any(area in f["area"] for area in area_descriptions):
                continue  # Skip this info block if none of the area descriptions match the filter

        # If the code reaches here, the info block has passed all filters
        logger.debug("Info block passed. Valid alert.")  # Log that the info block is valid
        return True  # Return True as the info block passed all filters

    logger.debug("No info block passed the filters.")  # Log if no info block passed
    return False  # Return False if no info block met the filter criteria
