import time
import requests
import json

API_URL = "http://localhost:8000/positions"

try:
    while True:
        response = requests.get(API_URL)
        current_time = time.strftime('%H:%M:%S')

        if response.status_code == 200:
            data = response.json()
            positions = data.get("positions", [])
            print(f"\n[{current_time}] Ricevute {len(positions)} posizioni:")
            for pos in positions:
                print(json.dumps(pos, indent=2))  # stampa ordinata
        else:
            print(f"[{current_time}] Errore {response.status_code}: {response.text}")
        
        time.sleep(5)
except KeyboardInterrupt:
    print("\nTest interrotto manualmente.")
