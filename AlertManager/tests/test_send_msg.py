import json
import sys
import os

# Aggiungi la cartella principale al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from AlertManager.api.send_msg import send_json_to_microservice

# Dati di esempio che vuoi inviare
test_data = {
    "alert_id": 12345,
    "type": "Severe Weather Warning",
    "location": "New York",
    "severity": "High",
    "message": "Tornado warning issued for New York."
}

# Test della funzione di invio messaggio
send_json_to_microservice(test_data)
