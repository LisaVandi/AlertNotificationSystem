import json
import sys
import os

# Add the main folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from AlertManager.api.send_msg import send_json_to_microservice

# Example data you want to send
test_data = {
    "alert_id": 12345,
    "type": "Severe Weather Warning",
    "location": "New York",
    "severity": "High",
    "message": "Tornado warning issued for New York."
}

# Test the message sending function
send_json_to_microservice(test_data)
