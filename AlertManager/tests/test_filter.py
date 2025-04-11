import sys
import os

# Aggiungi la cartella principale al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


from AlertManager.utils.filter import process_cap
# Crea un esempio di CAP alert (in formato dizionario)
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

# Carica e applica il filtro
result = process_cap(cap_alert)

# Mostra il risultato
if result:
    print("Alert passed the filter!")
else:
    print("Alert did not pass the filter.")
