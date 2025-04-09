import yaml
import xmltodict
from app.utils.cap_utils import filter_cap
from app.models.alert import Alert
from app.database import SessionLocal

def process_cap(cap_content: str):
    """
    Processes a CAP XML file by applying filtering rules and saving valid alerts.

    Args:
        cap_content (str): CAP XML content.

    Returns:
        dict: Result of the processing (accepted/rejected).
    """
    # Convert the CAP XML content to a dictionary using xmltodict
    cap_dict = xmltodict.parse(cap_content)

    # Load filtering rules from the YAML configuration
    with open("config/config.yaml", "r") as file:
        config = yaml.safe_load(file)
        rules = config["filtering_rules"]

    # Apply the filtering rules
    if not filter_cap(cap_dict, rules):
        # If the CAP does not pass the filtering rules, return rejection status
        return {"status": "rejected", "reason": "CAP did not pass filtering rules."}

    # If valid, save to database (simplified example)
    db = SessionLocal()
    alert_data = {
        "id": cap_dict["alert"]["identifier"],
        "severity": cap_dict["alert"]["info"]["severity"],
        "category": cap_dict["alert"]["info"]["category"],
        "urgency": cap_dict["alert"]["info"]["urgency"],
        "description": cap_dict["alert"]["info"]["description"],
        "timestamp": cap_dict["alert"]["sent"],
    }
    # Create and save a new alert object in the database
    new_alert = Alert(**alert_data)  # Create an Alert model instance
    db.add(new_alert)  # Add the alert to the session
    db.commit()  # Commit the transaction to save it in the database
    db.refresh(new_alert)  # Refresh to get the new alert's ID

    return {"status": "success", "alert_id": new_alert.id}  #Return success response
