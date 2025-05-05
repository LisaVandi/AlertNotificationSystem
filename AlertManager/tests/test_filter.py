import sys
import os

# Add the main folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from AlertManager.utils.filter import process_cap

# Create an example CAP alert (in dictionary format)
cap_alert = {
    "event": "Fire",
    "urgency": "Immediate",
    "severity": "Extreme",
    "certainty": "Observed",
    "area": "Building A",
    "responseType": "Evacuate",
    "status": "Actual",
    "messageType": "Alert",
    "scope": "Public"
}

# Load and apply the filter
result = process_cap(cap_alert)

# Show the result
if result:
    print("Alert passed the filter!")
else:
    print("Alert did not pass the filter.")
